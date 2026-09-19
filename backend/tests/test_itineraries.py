"""Mock Maps boundary and real AI2/SQL persistence tests."""
import os
import json
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.tests.test_backend import BackendFixture
from backend.services.place_service import search_places, normalize_category
from backend.services.itinerary_service import time_text
from ai.itinerary_planner.ai2_pipeline import run_ai2_pipeline


class ItineraryTests(BackendFixture):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.trip = self.create_trip()
        self.url = f"/api/trips/{self.trip}"

    def generate(self, **changes):
        return self.client.post(self.url + "/itinerary", json={"date": "2026-09-20", "user_conditions": [], **changes})

    def test_mock_places_and_normalization(self):
        places = search_places("성수", [])
        self.assertEqual(len(places), 8)
        self.assertTrue(all({"place_id", "name", "category", "keywords", "lat", "lng"} <= p.keys() for p in places))
        self.assertEqual(normalize_category("음식점"), "food")
        self.assertEqual(normalize_category("공원"), "outdoor")
        self.assertEqual(normalize_category("관광명소"), "sightseeing")
        self.assertEqual(normalize_category("unmapped"), "other")

    def test_generate_persist_get(self):
        with patch("backend.services.itinerary_service.run_ai2_pipeline", wraps=run_ai2_pipeline) as ai:
            response = self.generate()
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(ai.call_args.kwargs["profiles"][0]["user_id"], 1)
        self.assertEqual(len(ai.call_args.kwargs["place_candidates"]), 8)
        self.assertEqual(result["place_source"], "mock")
        self.assertEqual(set(result["preference_coverage"]), {"owner"})
        self.assertTrue(all(stop["related_users"] == ["owner"] for stop in result["schedule"]))
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [result])
        self.assertEqual(self.client.get(self.url + "/itineraries/" + result["itinerary_id"]).json(), result)
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM itinerary_places")).scalar_one(), 4)
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM places")).scalar_one(), 4)

    def test_same_day_replaces_atomically(self):
        first = self.generate().json()
        second = self.generate(user_conditions=["저녁"]).json()
        self.assertEqual(first["itinerary_id"], second["itinerary_id"])
        self.assertEqual(len(self.client.get(self.url + "/itineraries").json()), 1)
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM itinerary_places")).scalar_one(), 4)

    def test_map_fields_post_get_and_snapshot(self):
        candidates = [{**p, "source": "kakao", "address": "서울 성동구 테스트로 1"} for p in search_places("성수", [])]
        with patch("backend.services.itinerary_service.search_places", return_value=candidates):
            response = self.generate()
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["place_source"], "kakao")
        for stop in result["schedule"]:
            self.assertIsInstance(stop["latitude"], float)
            self.assertIsInstance(stop["longitude"], float)
            self.assertEqual(stop["address"], "서울 성동구 테스트로 1")
        with self.engine.begin() as db:
            self.assertEqual(db.execute(text("SELECT address FROM places LIMIT 1")).scalar_one(), "서울 성동구 테스트로 1")
            db.execute(text("UPDATE places SET latitude=0,address='changed'"))
        # Existing snapshot fields remain generation-time facts, not current place values.
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [result])
        self.assertEqual(self.client.get(self.url + "/itineraries/" + result["itinerary_id"]).json(), result)

    def test_old_snapshot_map_fields_backfilled(self):
        result = self.generate().json()
        for stop in result["schedule"]:
            for field in ("latitude", "longitude", "address"):
                stop.pop(field)
        with self.engine.begin() as db:
            db.execute(text("UPDATE trip_itineraries SET result_json=:snapshot"), {"snapshot": json.dumps(result)})
            db.execute(text("UPDATE places SET address='서울 성동구'"))
        restored = self.client.get(self.url + "/itineraries/" + result["itinerary_id"]).json()
        for before, after in zip(result["schedule"], restored["schedule"]):
            self.assertIsInstance(after["latitude"], float)
            self.assertEqual(after["address"], "서울 성동구")
            self.assertTrue(before.items() <= after.items())

    def test_missing_coordinates_remain_null(self):
        candidates = [{**p, "lat": None, "lng": None} for p in search_places("성수", [])]
        with patch("backend.services.itinerary_service.search_places", return_value=candidates):
            result = self.generate().json()
        self.assertTrue(all(stop["latitude"] is None and stop["longitude"] is None for stop in result["schedule"]))
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [result])

    def test_ai_failure_no_persistence(self):
        with patch("backend.services.itinerary_service.run_ai2_pipeline", side_effect=RuntimeError("secret")):
            response = self.generate()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret", response.text)
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [])

    def test_late_db_failure_preserves_old_itinerary(self):
        old = self.generate().json()
        # Fail child INSERT after the existing children have been deleted.
        from sqlalchemy import event
        def fail(conn, cursor, statement, parameters, context, executemany):
            if "INSERT INTO itinerary_places" in statement:
                raise SQLAlchemyError("private")
        event.listen(self.engine, "before_cursor_execute", fail)
        try:
            response = self.generate(user_conditions=["changed"])
        finally:
            event.remove(self.engine, "before_cursor_execute", fail)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [old])
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM itinerary_places")).scalar_one(), 4)

    def test_invalid_date_time_and_missing(self):
        self.assertEqual(self.generate(date="2026-09-21").status_code, 400)
        self.assertEqual(self.generate(date="bad").status_code, 400)
        self.assertEqual(self.client.get(self.url + "/itineraries/missing").status_code, 404)
        self.assertEqual(time_text(timedelta(hours=13)), "13:00")
        with self.engine.begin() as db:
            db.execute(text("UPDATE trips SET day_end_time='12:00:00'"))
        self.assertEqual(self.generate().status_code, 400)

    def test_provider_failure_is_explicit(self):
        from backend.services.common import ServiceError
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": "test-placeholder"}), patch(
            "backend.services.place_service.search_provider_places", side_effect=ServiceError(503, "Provider unavailable")
        ):
            self.assertEqual(self.generate().status_code, 503)

    def test_preferences_change_during_generation_rejected(self):
        def generate_and_mutate(*args, **kwargs):
            result = run_ai2_pipeline(*args, **kwargs)
            with self.engine.begin() as db:
                db.execute(text("INSERT INTO user_preferences (preference_id,user_id,category_scores,tag_scores) VALUES ('changed','owner',:scores, '{}')"), {"scores": '{"cafe":1}'})
            return result
        with patch("backend.services.itinerary_service.run_ai2_pipeline", side_effect=generate_and_mutate):
            self.assertEqual(self.generate().status_code, 409)
        self.assertEqual(self.client.get(self.url + "/itineraries").json(), [])
