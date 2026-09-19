"""Authentication contracts using SQLite and ephemeral test signing keys."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt
from sqlalchemy import text
from backend.auth import create_access_token
from backend.tests.test_backend import BackendFixture


class AuthTests(BackendFixture):
    def setUp(self) -> None:
        super().setUp()
        self.client.headers.pop("Authorization", None)
        self.credentials = {"email": "auth@example.com", "password": secrets.token_urlsafe(12)}

    def signup(self) -> dict:
        response = self.client.post("/api/users", json={"name": "Auth user", **self.credentials})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_empty_database_signup_login_me(self):
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM users"))
        user = self.signup()
        response = self.client.post("/api/auth/login", json=self.credentials)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["user_id"], user["user_id"])
        self.assertNotIn("password_hash", data["user"])
        claims = jwt.decode(data["access_token"], os.environ["JWT_SECRET"], algorithms=["HS256"])
        self.assertEqual(claims["sub"], user["user_id"])
        self.client.headers["Authorization"] = "Bearer " + data["access_token"]
        self.assertEqual(self.client.get("/api/auth/me").json(), data["user"])
        self.assertEqual(self.client.get("/api/users").status_code, 200)
        self.assertEqual(self.client.post("/api/trips", json={**self.body, "owner_user_id": user["user_id"]}).status_code, 201)

    def test_duplicate_signup(self):
        self.signup()
        response = self.client.post("/api/users", json={"name": "Other", **self.credentials})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "이미 존재하는 이메일입니다.")

    def test_wrong_password_and_nonexistent_email_same_failure(self):
        self.signup()
        wrong = self.client.post("/api/auth/login", json={**self.credentials, "password": "wrong-password"})
        missing = self.client.post("/api/auth/login", json={**self.credentials, "email": "absent@example.com"})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.json(), missing.json())

    def test_inactive_and_invalid_stored_hash_fail_safely(self):
        user = self.signup()
        self.authenticate_as(user["user_id"])
        with self.engine.begin() as db:
            db.execute(text("UPDATE users SET is_active=FALSE WHERE user_id=:id"), {"id": user["user_id"]})
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json=self.credentials).status_code, 401)
        with self.engine.begin() as db:
            db.execute(text("UPDATE users SET is_active=TRUE,password_hash='!reset-required' WHERE user_id=:id"), {"id": user["user_id"]})
        self.assertEqual(self.client.post("/api/auth/login", json=self.credentials).status_code, 401)

    def test_me_requires_token_and_rejects_invalid_expired_or_wrong_algorithm(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/users").status_code, 401)
        now = datetime.now(timezone.utc)
        secret = os.environ["JWT_SECRET"]
        tokens = ["invalid", jwt.encode({"sub": "owner", "exp": now - timedelta(minutes=1)}, secret, algorithm="HS256"),
                  jwt.encode({"sub": "owner"}, secret, algorithm="HS256"),
                  jwt.encode({"sub": "owner", "exp": now + timedelta(minutes=1)}, secret, algorithm="HS384"),
                  jwt.encode({"sub": "owner", "exp": now + timedelta(minutes=1)}, secrets.token_urlsafe(48), algorithm="HS256")]
        for token in tokens:
            self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code, 401)

    def test_trip_owner_spoofing_and_anonymous_create_rejected(self):
        self.assertEqual(self.client.post("/api/trips", json=self.body).status_code, 401)
        self.authenticate_as("owner")
        self.assertEqual(self.client.post("/api/trips", json={**self.body, "owner_user_id": "other"}).status_code, 403)
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM trips")).scalar_one(), 0)

    def test_shortform_spoofing_rejected_before_ai(self):
        trip = self.create_trip()
        self.client.post(f"/api/trips/{trip}/members", json={"user_id": "other"})
        with patch("backend.routers.shortforms.service.save_shortform") as save:
            response = self.client.post(f"/api/trips/{trip}/shortforms", json={"user_id": "other", "url": "https://youtu.be/abcdefghijk"})
            self.assertEqual(response.status_code, 403)
            self.client.headers.pop("Authorization", None)
            self.assertEqual(self.client.post(f"/api/trips/{trip}/shortforms", json={"user_id": "owner", "url": "https://youtu.be/abcdefghijk"}).status_code, 401)
            save.assert_not_called()

    def test_missing_secret_fails_closed(self):
        self.signup()
        with patch.dict(os.environ, {"JWT_SECRET": ""}):
            self.assertEqual(self.client.post("/api/auth/login", json=self.credentials).status_code, 503)

    def test_deleted_user_token_rejected(self):
        token = create_access_token("other")
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM users WHERE user_id='other'"))
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code, 401)
