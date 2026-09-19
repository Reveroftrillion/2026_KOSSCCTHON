"""Opt-in MySQL roundtrip on a manually provisioned, dedicated *_test database."""
import copy
import os
import re
import unittest
import uuid
import secrets
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from backend.main import app, get_db
from backend.auth import create_access_token
from backend.services.place_service import search_places


@unittest.skipUnless(os.getenv("RUN_MYSQL_INTEGRATION_TESTS") == "1", "MySQL integration is opt-in")
class MySQLIntegrationTests(unittest.TestCase):
    def test_real_mysql_persistence(self):
        """Exercise JSON, TIME, UUIDs, upsert, constraints and cascades without DDL."""
        auth_env = patch.dict(os.environ, {"JWT_SECRET": secrets.token_urlsafe(48), "JWT_EXPIRE_MINUTES": "480"})
        auth_env.start()
        self.addCleanup(auth_env.stop)
        database = os.getenv("MYSQL_TEST_DB_NAME", "")
        if not re.fullmatch(r"[a-zA-Z0-9_]+_test", database) or database.lower() == os.getenv("DB_NAME", "tripclip").lower():
            self.fail("MYSQL_TEST_DB_NAME must be a separate *_test database; no connection attempted")
        engine = create_engine(URL.create("mysql+pymysql", host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")), username=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""), database=database),
            connect_args={"charset": "utf8mb4", "connect_timeout": 5}, hide_parameters=True)
        self.addCleanup(engine.dispose)
        try:
            with engine.connect() as db:
                self.assertEqual(db.execute(text("SELECT DATABASE()")).scalar_one(), database)
                engines = db.execute(text("SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=:db"), {"db": database}).scalars().all()
                self.assertTrue(engines and all(item == "InnoDB" for item in engines), "Apply schema manually using InnoDB first")
                db.execute(text("SELECT result_json FROM trip_itineraries LIMIT 0"))
                db.execute(text("SELECT user_scores FROM itinerary_places LIMIT 0"))
                db.execute(text("SELECT content_id FROM shortform_contents LIMIT 0"))
        except Exception:
            self.fail("MySQL preflight failed; verify dedicated test DB, credentials and manually applied schema")
        factory = sessionmaker(bind=engine)
        def override_db():
            with factory() as session:
                yield session
        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_db
        users = [str(uuid.uuid4()) for _ in range(3)]
        run_id = str(uuid.uuid4())
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}):
            places = copy.deepcopy(search_places("성수", []))
        for place in places:
            place["place_id"] = run_id + ":" + place["place_id"]
        place_ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, "tripclip:mock:" + p["place_id"])) for p in places]
        try:
            with engine.begin() as db:
                for user in users:
                    db.execute(text("INSERT INTO users (user_id,name,email,password_hash) VALUES (:id,'MySQL test',:email,'unused')"),
                               {"id": user, "email": user + "@example.com"})
            with TestClient(app) as client:
                client.headers["Authorization"] = "Bearer " + create_access_token(users[0])
                self.assertEqual(client.get("/health/db").status_code, 200)
                trip_response = client.post("/api/trips", json={"trip_name": "MySQL test", "region": "성수",
                    "start_date": "2026-09-20", "end_date": "2026-09-20", "owner_user_id": users[0],
                    "day_start_time": "13:00:00", "day_end_time": "20:00:00", "description": ""})
                self.assertEqual(trip_response.status_code, 201)
                base = "/api/trips/" + trip_response.json()["trip_id"]
                for user in users[1:]:
                    self.assertEqual(client.post(base + "/members", json={"user_id": user}).status_code, 201)
                analysis = {"metadata": {"title": "성수 카페"}, "analysis": {"category": "cafe", "keywords": ["dessert"]}}
                with patch("backend.services.preference_service.analyze_youtube_url", return_value=analysis):
                    for user in users:
                        client.headers["Authorization"] = "Bearer " + create_access_token(user)
                        body = {"user_id": user, "url": "https://youtu.be/abcdefghijk"}
                        self.assertEqual(client.post(base + "/shortforms", json=body).status_code, 201)
                        self.assertEqual(client.post(base + "/shortforms", json=body).status_code, 409)
                with patch("backend.services.itinerary_service.search_places", return_value=places):
                    for _ in range(2):
                        response = client.post(base + "/itinerary", json={"date": "2026-09-20", "user_conditions": []})
                        self.assertEqual(response.status_code, 201)
                        result = response.json()
                        self.assertEqual(client.get(base + "/itineraries/" + result["itinerary_id"]).json(), result)
                with engine.connect() as db:
                    for stop in result["schedule"]:
                        coordinate = db.execute(text("SELECT latitude FROM places WHERE place_id=:id"), {"id": stop["place_id"]}).scalar_one()
                        self.assertIsNotNone(coordinate)
                self.assertEqual(client.delete(base).status_code, 200)
                for user in users:
                    self.assertEqual(client.get(f"/api/users/{user}/preferences").json()["category_preferences"], {})
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            # Only this run's generated UUIDs; never truncate/drop or delete other fixtures.
            with engine.begin() as db:
                for user in users:
                    db.execute(text("DELETE FROM users WHERE user_id=:id"), {"id": user})
                for place_id in place_ids:
                    db.execute(text("DELETE FROM places WHERE place_id=:id"), {"id": place_id})
