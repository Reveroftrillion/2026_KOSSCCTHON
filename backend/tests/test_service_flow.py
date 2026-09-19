"""Three-user Backend smoke: mocked AI1 transport, real preference math and AI2."""
import os
from unittest.mock import patch
from backend.tests.test_backend import BackendFixture


class ServiceFlowTests(BackendFixture):
    def test_full_service_flow(self):
        users = []
        for index in range(3):
            response = self.client.post("/api/users", json={"name": f"User {index}", "email": f"smoke{index}@example.com", "password": "smoke-password"})
            self.assertEqual(response.status_code, 201)
            users.append(response.json()["user_id"])
        response = self.client.post("/api/trips", json={**self.body, "owner_user_id": users[0]})
        self.assertEqual(response.status_code, 201)
        trip = response.json()["trip_id"]
        base = f"/api/trips/{trip}"
        for user in users[1:]:
            self.assertEqual(self.client.post(base + "/members", json={"user_id": user}).status_code, 201)
        self.assertEqual(len(self.client.get(base + "/members").json()["data"]), 3)
        for index, user in enumerate(users):
            category, keyword = [("cafe", "dessert"), ("outdoor", "nature"), ("exhibition", "art")][index]
            output = {"metadata": {"title": category}, "analysis": {"category": category, "keywords": [keyword], "place_name": None}}
            with patch("backend.services.preference_service.analyze_youtube_url", return_value=output):
                for video in range(2):
                    response = self.client.post(base + "/shortforms", json={"user_id": user, "url": f"https://youtu.be/abcdefghi{index}{video}"})
                    self.assertEqual(response.status_code, 201, response.text)
                    self.assertEqual(response.json()["user_id"], user)
        self.assertEqual(len(self.client.get(base + "/shortforms").json()["data"]), 6)
        profiles = self.client.get(base + "/preferences").json()
        self.assertEqual({p["user_id"] for p in profiles}, set(users))
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}):
            response = self.client.post(base + "/itinerary", json={"date": "2026-09-20", "user_conditions": []})
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(set(result["preference_coverage"]), set(users))
        self.assertEqual(set(result["preference_reflection"]), set(users))
        self.assertEqual(len(result["schedule"]), 4)
        for stop in result["schedule"]:
            self.assertEqual(set(stop["user_scores"]), set(users))
            self.assertTrue(set(stop["related_users"]) <= set(users))
            self.assertNotIn("번 사용자", stop["reason"])
        self.assertEqual(self.client.get(base + "/itineraries/" + result["itinerary_id"]).json(), result)
