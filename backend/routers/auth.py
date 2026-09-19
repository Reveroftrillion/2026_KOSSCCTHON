"""Public password login and authenticated identity endpoint."""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth import create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Check bcrypt credentials and issue an access token without logging secrets."""
    user = db.execute(text("SELECT user_id,name,email,password_hash,is_active FROM users WHERE email=:email"),
                      {"email": body.email.strip()}).mappings().first()
    valid = False
    if user and user["is_active"] and len(body.password.encode("utf-8")) <= 72:
        try:
            valid = bcrypt.checkpw(body.password.encode("utf-8"), user["password_hash"].encode("utf-8"))
        except (ValueError, TypeError, AttributeError):
            valid = False
    if not valid:
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user["user_id"]), "token_type": "bearer",
            "user": {key: user[key] for key in ("user_id", "name", "email")}}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the authenticated user independently of any client-selected ID."""
    return current_user
