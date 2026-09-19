"""Three-user identity, persistence and operational API contracts."""
import copy
import os
import uuid
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.tests.test_backend import BackendFixture
from backend.services.itinerary_service import restore_ids, persist_places
from backend.services.preference_service import ai_user_id
from ai.itinerary_planner.ai2_pipeline import run_ai2_pipeline


class ReadinessTests(BackendFixture):
    def test_db_health(self):
        self.assertEqual(self.client.get("/health/db").json(), {"status": "ok", "database": "connected"})

    def test_db_health_error_safe(self):
        with patch("sqlalchemy.orm.Session.execute", side_effect=SQLAlchemyError("private-password")):
            response = self.client.get("/health/db")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-password", response.text)

    def test_openapi_routes(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for path, methods in {"/api/users": ["post"], "/api/trips": ["post"],
                              "/api/trips/{trip_id}/members": ["post", "get"],
                              "/api/trips/{trip_id}/shortforms": ["post", "get"],
                              "/api/users/{user_id}/preferences": ["get"], "/api/trips/{trip_id}/preferences": ["get"],
                              "/api/trips/{trip_id}/itinerary": ["post"], "/api/trips/{trip_id}/itineraries": ["get"]}.items():
            self.assertTrue(set(methods) <= paths[path].keys(), path)

    def test_three_uuid_ai_and_persistence_roundtrip(self):
        ids = [str(uuid.uuid4()) for _ in range(3)]
        with self.engine.begin() as db:
            for index, user in enumerate(ids):
                db.execute(text("INSERT INTO users (user_id,name,email,password_hash) VALUES (:id,'test',:email,'unused')"),
                           {"id": user, "email": f"{user}@example.com"})
                db.execute(text("INSERT INTO user_preferences (preference_id,user_id,category_scores,tag_scores) VALUES (:id,:id,:scores,'{}')"),
                           {"id": user, "scores": ['{"cafe":1}', '{"food":1}', '{"shopping":1}'][index]})
        encoded = [ai_user_id(user) for user in ids]
        self.assertEqual(len(set(encoded)), 3)
        self.assertTrue(all(user > 0 for user in encoded))
        self.body["owner_user_id"] = ids[0]
        trip = self.create_trip()
        for user in ids[1:]:
            self.assertEqual(self.client.post(f"/api/trips/{trip}/members", json={"user_id": user}).status_code, 201)
        captured = {}
        def capture(*args, **kwargs):
            captured["profiles"] = copy.deepcopy(kwargs["profiles"])
            captured["raw"] = run_ai2_pipeline(*args, **kwargs)
            return captured["raw"]
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}), patch("backend.services.itinerary_service.run_ai2_pipeline", side_effect=capture):
            response = self.client.post(f"/api/trips/{trip}/itinerary", json={"date": "2026-09-20", "user_conditions": []})
        self.assertEqual(response.status_code, 201, response.text)
        saved = response.json()
        expected = restore_ids(captured["raw"], dict(enumerate(sorted(ids), 1)))
        for field in ("preference_coverage", "preference_reflection"):
            self.assertEqual(saved[field], expected[field])
            self.assertEqual(set(saved[field]), set(ids))
        for before, after in zip(expected["schedule"], saved["schedule"]):
            for field in ("reason", "related_users", "user_scores", "group_score"):
                self.assertEqual(before[field], after[field])
            self.assertEqual(set(after["user_scores"]), set(ids))
            self.assertTrue(set(after["related_users"]) <= set(ids))
        self.assertEqual(self.client.get(f"/api/trips/{trip}/itineraries/{saved['itinerary_id']}").json(), saved)

    def test_kakao_stable_place_upsert(self):
        from sqlalchemy.orm import Session
        place = {"place_id": "123", "name": "카페", "category": "cafe", "lat": 37.5, "lng": 127.0, "source": "kakao"}
        with Session(self.engine) as db:
            first = persist_places(db, [place], "성수")
            second = persist_places(db, [{**place, "name": "변경"}], "성수")
            self.assertEqual(first, second)
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM places")).scalar_one(), 1)
            self.assertEqual(db.execute(text("SELECT place_name FROM places")).scalar_one(), "변경")
