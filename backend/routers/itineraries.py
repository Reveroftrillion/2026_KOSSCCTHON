"""Itinerary generation and retrieval HTTP contracts."""
from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.common import ServiceError
from backend.services.itinerary_service import generate_and_save, get_itineraries

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["Itineraries"])


class ItineraryRequest(BaseModel):
    date: str = Field(examples=["2026-09-20"])
    user_conditions: list[str] = Field(default_factory=list)


@router.post("/itinerary", status_code=201)
def generate(trip_id: str, body: ItineraryRequest, db: Session = Depends(get_db)) -> dict:
    try:
        target = date.fromisoformat(body.date)
    except ValueError:
        raise ServiceError(400, "날짜는 YYYY-MM-DD 형식이어야 합니다.") from None
    return generate_and_save(db, trip_id, target, body.user_conditions)


@router.get("/itineraries")
def listing(trip_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return get_itineraries(db, trip_id)


@router.get("/itineraries/{itinerary_id}")
def detail(trip_id: str, itinerary_id: str, db: Session = Depends(get_db)) -> dict:
    return get_itineraries(db, trip_id, itinerary_id)[0]
