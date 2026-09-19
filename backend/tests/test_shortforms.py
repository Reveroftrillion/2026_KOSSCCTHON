"""Content persistence and AI1 parity without external requests."""
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.tests.test_backend import BackendFixture
from backend.services.preference_service import recalculate, ai_user_id
from ai.preference_analyzer import calculate_preferences, AnalyzedContent


class ShortformTests(BackendFixture):
    def setUp(self):
        super().setUp()
        self.trip = self.create_trip()
        self.url = f"/api/trips/{self.trip}/shortforms"
        self.ai = patch("backend.services.preference_service.analyze_youtube_url", return_value={
            "metadata": {"title": "카페"}, "analysis": {"category": "cafe", "keywords": ["date", "date"], "place_name": None}})
        self.mock = self.ai.start()
        self.addCleanup(self.ai.stop)

    def save(self, index=0, user="owner"):
        return self.client.post(self.url, json={"user_id": user, "url": f"https://youtu.be/abcdefghij{index}"})

    def test_save_list_duplicate(self):
        result = self.save()
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["analysis"]["user_id"], "owner")
        self.mock.assert_called_once_with(ai_user_id("owner"), "https://www.youtube.com/watch?v=abcdefghij0")
        self.assertEqual(self.save().status_code, 409)
        self.assertEqual(self.mock.call_count, 1)
        items = self.client.get(self.url).json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["keywords"], ["date"])
        self.assertIsNone(items[0]["place_name"])

    def test_reject_nonmember_and_bad_url(self):
        self.assertEqual(self.save(user="other").status_code, 403)
        self.assertEqual(self.client.post(self.url, json={"user_id": "owner", "url": "invalid"}).status_code, 400)
        self.mock.assert_not_called()

    def test_ai_failure_no_save(self):
        self.mock.side_effect = RuntimeError("private-secret")
        response = self.save()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private-secret", response.text)
        self.assertEqual(self.client.get(self.url).json()["data"], [])

    def test_preference_parity_and_upsert(self):
        self.save(0)
        self.save(1)
        self.mock.return_value["analysis"] = {"category": "food", "keywords": ["local"]}
        self.save(2)
        expected = calculate_preferences(1, [AnalyzedContent(category="cafe", keywords=["date"])] * 2 + [AnalyzedContent(category="food", keywords=["local"])]).model_dump()
        actual = self.client.get("/api/users/owner/preferences").json()
        self.assertEqual(actual["category_preferences"], expected["category_preferences"])
        self.assertEqual(actual["keyword_preferences"], expected["keyword_preferences"])
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM user_preferences")).scalar_one(), 1)

    def test_delete_recalculates(self):
        content = self.save().json()["content_id"]
        result = self.client.delete(self.url + "/" + content)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["preference_profile"]["category_preferences"], {})
        self.assertEqual(result.json()["preference_profile"]["keyword_preferences"], {})
        self.assertEqual(self.client.delete(self.url + "/" + content).status_code, 404)

    def test_empty_member_profile(self):
        self.client.post(f"/api/trips/{self.trip}/members", json={"user_id": "other"})
        self.save()
        profiles = self.client.get(f"/api/trips/{self.trip}/preferences").json()
        self.assertEqual(len(profiles), 2)
        self.assertEqual(next(p for p in profiles if p["user_id"] == "other")["category_preferences"], {})

    def test_database_failure_rolls_back(self):
        from sqlalchemy.exc import SQLAlchemyError
        with patch("backend.services.preference_service.recalculate", side_effect=SQLAlchemyError("secret")):
            response = self.save()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret", response.text)
        self.assertEqual(self.client.get(self.url).json()["data"], [])

    def test_history_across_trips(self):
        self.save()
        second = self.create_trip()
        self.mock.return_value["analysis"] = {"category": "food", "keywords": []}
        response = self.client.post(f"/api/trips/{second}/shortforms", json={"user_id": "owner", "url": "https://youtu.be/abcdefghij0"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["preference_profile"]["category_preferences"], {"cafe": .5, "food": .5})

    def test_delete_one_preserves_other_content(self):
        first = self.save(0).json()["content_id"]
        self.mock.return_value["analysis"] = {"category": "food", "keywords": ["local"]}
        self.save(1)
        result = self.client.delete(self.url + "/" + first)
        self.assertEqual(result.json()["preference_profile"]["category_preferences"], {"food": 1.0})

    def test_missing_user_and_trip(self):
        self.assertEqual(self.save(user="missing").status_code, 404)
        self.assertEqual(self.client.post("/api/trips/missing/shortforms", json={"user_id": "owner", "url": "https://youtu.be/abcdefghij0"}).status_code, 404)
        self.mock.assert_not_called()

    def test_video_id_case_is_distinct(self):
        self.assertEqual(self.save().status_code, 201)
        response = self.client.post(self.url, json={"user_id": "owner", "url": "https://youtu.be/Abcdefghij0"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get(self.url).json()["data"]), 2)
