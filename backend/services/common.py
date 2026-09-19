"""Small shared DB helpers and safe service errors."""

import json
from contextlib import contextmanager
from typing import Any, Iterator
from sqlalchemy import text
from sqlalchemy.orm import Session


class ServiceError(Exception):
    """A public, credential-free service failure."""
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def row(db: Session, sql: str, **params: Any) -> dict | None:
    """Return a detached SQL row."""
    found = db.execute(text(sql), params).mappings().first()
    return dict(found) if found else None


def require(db: Session, table: str, identifier: str, *, lock: bool = False) -> dict:
    """Fetch a user/trip; optionally serialize writes on MySQL."""
    key = {"users": "user_id", "trips": "trip_id"}[table]
    suffix = " FOR UPDATE" if lock and db.bind.dialect.name == "mysql" else ""
    result = row(db, f"SELECT * FROM {table} WHERE {key}=:id" + suffix, id=identifier)
    if not result:
        raise ServiceError(404, f"{table} 항목을 찾을 수 없습니다.")
    return result


def member(db: Session, trip_id: str, user_id: str) -> None:
    """Verify trip, user and membership."""
    require(db, "trips", trip_id)
    require(db, "users", user_id)
    if not row(db, "SELECT user_id FROM trip_members WHERE trip_id=:trip AND user_id=:user", trip=trip_id, user=user_id):
        raise ServiceError(403, "여행 멤버만 콘텐츠를 저장할 수 있습니다.")


def decode(value: Any, default: Any) -> Any:
    """Support MySQL drivers returning JSON either decoded or as text."""
    return default if value is None else json.loads(value) if isinstance(value, str) else value


@contextmanager
def transaction(db: Session) -> Iterator[None]:
    """Commit once, rolling all changes back on any failure."""
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
