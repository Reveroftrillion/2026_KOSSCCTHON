"""HTTP/SQL contract tests using schema.sql-derived SQLite tables, not a live MySQL DB."""

from datetime import datetime
from pathlib import Path
import re
import unittest

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app, get_db, hash_password


class BackendFixture(unittest.TestCase):
    """Run actual endpoint SQL with only MySQL DDL syntax adapted for SQLite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)

    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(self.engine, "connect")
        def configure(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("NOW", 0, lambda: datetime.now().isoformat())

        schema = (Path(__file__).resolve().parents[1] / "db/schema.sql").read_text(encoding="utf-8")
        schema = re.sub(r"--[^\n]*", "", schema)
        with self.engine.begin() as connection:
            for table in re.findall(r"CREATE TABLE (\w+)", schema):
                ddl = re.search(rf"CREATE TABLE {table} \(.*?\);", schema, re.S).group()
                ddl = re.sub(r",\s*INDEX \w+ \([^)]*\)", "", ddl)
                ddl = re.sub(r"UNIQUE KEY \w+", "UNIQUE", ddl)
                ddl = ddl.replace("CHARACTER SET ascii COLLATE ascii_bin", "")
                connection.exec_driver_sql(ddl)
            for user in ("owner", "other"):
                connection.execute(text("INSERT INTO users (user_id, name, email, password_hash) VALUES (:id, :id, :email, 'test-only')"), {"id": user, "email": user + "@example.com"})
        factory = sessionmaker(bind=self.engine)

        def override_db():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        self.body = {"trip_name": "성수 여행", "region": "성수", "start_date": "2026-09-20", "end_date": "2026-09-20",
                     "owner_user_id": "owner", "day_start_time": "13:00:00", "day_end_time": "20:00:00", "description": ""}

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def create_trip(self) -> str:
        response = self.client.post("/api/trips", json=self.body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["trip_id"]

class BackendTests(BackendFixture):
    def test_post_user(self) -> None:
        response = self.client.post("/api/users", json={"name": "테스트", "email": "new@example.com", "password": "example-password"})
        self.assertEqual(response.status_code, 201, response.text)
        with self.engine.connect() as connection:
            hashed = connection.execute(text("SELECT password_hash FROM users WHERE user_id=:id"), {"id": response.json()["user_id"]}).scalar_one()
        self.assertTrue(bcrypt.checkpw(b"example-password", hashed.encode()))
        self.assertNotIn("password", response.json())

    def test_get_user(self) -> None:
        response = self.client.get("/api/users/owner")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIsNone(data["bio"])
        self.assertIsNone(data["profile_image_url"])
        self.assertTrue(data["is_active"])
        self.assertNotIn("password_hash", data)

    def test_post_trip(self) -> None:
        trip_id = self.create_trip()
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT owner_user_id FROM trips WHERE trip_id=:id"), {"id": trip_id}).scalar_one(), "owner")

    def test_get_trip(self) -> None:
        response = self.client.get("/api/trips/" + self.create_trip())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["owner_user_id"], "owner")
        self.assertNotIn("user_id", response.json()["data"])

    def test_owner_trips(self) -> None:
        self.create_trip()
        self.assertEqual(self.client.get("/api/users/owner/trips").json()["count"], 1)
        self.assertEqual(self.client.get("/api/users/other/trips").json()["count"], 0)

    def test_put_trip(self) -> None:
        trip_id = self.create_trip()
        response = self.client.put("/api/trips/" + trip_id, json={**self.body, "owner_user_id": "other", "description": "수정"})
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get("/api/trips/" + trip_id).json()["data"]
        self.assertEqual((data["owner_user_id"], data["description"]), ("other", "수정"))

    def test_delete_trip(self) -> None:
        trip_id = self.create_trip()
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO trip_members (trip_member_id,trip_id,user_id) VALUES ('m',:id,'other')"), {"id": trip_id})
        self.assertEqual(self.client.delete("/api/trips/" + trip_id).status_code, 200)
        self.assertEqual(self.client.get("/api/trips/" + trip_id).status_code, 404)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM trip_members")).scalar_one(), 0)

    def test_validation_and_missing_records(self) -> None:
        old_body = {**self.body, "user_id": "owner"}
        del old_body["owner_user_id"]
        self.assertEqual(self.client.post("/api/trips", json=old_body).status_code, 422)
        self.assertEqual(self.client.post("/api/trips", json={**self.body, "owner_user_id": "missing"}).status_code, 404)
        self.assertEqual(self.client.get("/api/users/missing").status_code, 404)
        self.assertEqual(self.client.delete("/api/trips/missing").status_code, 404)
        trip_id = self.create_trip()
        for change in ({"day_start_time": "bad"}, {"start_date": "2026-09-21"}):
            self.assertEqual(self.client.put("/api/trips/" + trip_id, json={**self.body, **change}).status_code, 400)

    def test_password_limit_and_duplicate_email(self) -> None:
        self.assertEqual(self.client.post("/api/users", json={"name": "x", "email": "x", "password": "가" * 25}).status_code, 422)
        self.assertEqual(self.client.post("/api/users", json={"name": "x", "email": "owner@example.com", "password": "example-password"}).status_code, 400)
        self.assertNotEqual(hash_password("example-password"), hash_password("example-password"))

    def test_openapi_owner_contract(self) -> None:
        schema = self.client.get("/openapi.json").json()["components"]["schemas"]["TripCreateRequest"]
        self.assertIn("owner_user_id", schema["required"])
        self.assertNotIn("user_id", schema["properties"])
        self.assertIn("owner_user_id", schema["example"])


if __name__ == "__main__":
    unittest.main()
