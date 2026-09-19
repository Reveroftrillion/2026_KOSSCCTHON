"""Persistent preference lookup endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.preference_service import get_profile, trip_profiles

router = APIRouter(tags=["Preferences"])


@router.get("/api/users/{user_id}/preferences")
def user_preferences(user_id: str, db: Session = Depends(get_db)) -> dict:
    return get_profile(db, user_id)


@router.get("/api/trips/{trip_id}/preferences")
def group_preferences(trip_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return trip_profiles(db, trip_id)
