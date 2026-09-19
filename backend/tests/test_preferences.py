"""Persistent preferences remain correct after trip lifecycle changes."""
from unittest.mock import patch
from backend.tests.test_backend import BackendFixture
from backend.services.preference_service import ai_user_id


class PreferenceTests(BackendFixture):
    def test_uuid_adapter_is_deterministic_and_distinct(self):
        first = "ea9f7e10-1234-4000-8000-000000000001"
        second = "ea9f7e10-1234-4000-8000-000000000002"
        self.assertGreater(ai_user_id(first), 0)
        self.assertEqual(ai_user_id(first), ai_user_id(first))
        self.assertNotEqual(ai_user_id(first), ai_user_id(second))

    def test_trip_delete_recalculates_remaining_history(self):
        trip = self.create_trip()
        output = {"metadata": {"title": "food"}, "analysis": {"category": "food", "keywords": ["local"]}}
        with patch("backend.services.preference_service.analyze_youtube_url", return_value=output):
            result = self.client.post(f"/api/trips/{trip}/shortforms", json={"user_id": "owner", "url": "https://youtu.be/abcdefghij0"})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/trips/{trip}").status_code, 200)
        self.assertEqual(self.client.get("/api/users/owner/preferences").json()["category_preferences"], {})

    def test_missing_user_trip_and_owner_transfer(self):
        self.assertEqual(self.client.get("/api/users/missing/preferences").status_code, 404)
        self.assertEqual(self.client.get("/api/trips/missing/preferences").status_code, 404)
        trip = self.create_trip()
        self.client.put(f"/api/trips/{trip}", json={**self.body, "owner_user_id": "other"})
        profiles = self.client.get(f"/api/trips/{trip}/preferences").json()
        self.assertEqual({p["user_id"] for p in profiles}, {"owner", "other"})
