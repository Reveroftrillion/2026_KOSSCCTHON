"""HS256 access tokens and an active-user dependency; no persistent sessions."""
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import get_db

bearer = HTTPBearer(auto_error=False)


def jwt_secret() -> str:
    """Fail closed when the deployment secret is absent or too short."""
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise HTTPException(503, "인증 서버 설정을 확인해주세요.")
    return secret


def unauthorized() -> HTTPException:
    """Use the same public response for missing, expired and invalid credentials."""
    return HTTPException(401, "로그인이 필요합니다.", headers={"WWW-Authenticate": "Bearer"})


def create_access_token(user_id: str) -> str:
    """Issue a time-limited JWT containing the Backend user UUID."""
    try:
        minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
        if minutes <= 0:
            raise ValueError
    except ValueError:
        raise HTTPException(503, "인증 서버 설정을 확인해주세요.") from None
    now = datetime.now(timezone.utc)
    try:
        expires = now + timedelta(minutes=minutes)
    except OverflowError:
        raise HTTPException(503, "인증 서버 설정을 확인해주세요.") from None
    return jwt.encode({"sub": user_id, "iat": now, "exp": expires}, jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> str:
    """Verify signature, expiration and subject with a fixed allowed algorithm."""
    secret = jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})
        subject = payload["sub"]
        if not isinstance(subject, str) or not 0 < len(subject) <= 36:
            raise ValueError
        return subject
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve each token to a still-existing, active user; never expose the hash."""
    if credentials is None:
        raise unauthorized()
    user_id = decode_access_token(credentials.credentials)
    user = db.execute(text("SELECT user_id,name,email,is_active FROM users WHERE user_id=:id"), {"id": user_id}).mappings().first()
    if not user or not user["is_active"]:
        raise unauthorized()
    return {key: user[key] for key in ("user_id", "name", "email")}


def require_same_user(user_id: str, current_user: dict) -> None:
    """Reject impersonation while keeping the existing request body contract."""
    if user_id != current_user["user_id"]:
        raise HTTPException(403, "로그인한 사용자로만 요청할 수 있습니다.")
