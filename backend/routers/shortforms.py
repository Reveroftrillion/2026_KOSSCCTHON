"""Shortform HTTP boundary."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services import preference_service as service

router = APIRouter(prefix="/api/trips/{trip_id}/shortforms", tags=["Shortforms"])


class ShortformRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    url: str = Field(min_length=1, max_length=500)

class ShortformUpdateRequest(BaseModel):
    place_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=50)
    keywords: list[str] | None = None
    recommended_time: str | None = Field(default=None, max_length=50)

@router.post("", status_code=201)
def create(trip_id: str, body: ShortformRequest, db: Session = Depends(get_db)) -> dict:
    return service.save_shortform(db, trip_id, body.user_id, body.url)


@router.get("")
def listing(trip_id: str, db: Session = Depends(get_db)) -> dict:
    return {"status": "success", "data": service.list_shortforms(db, trip_id)}

@router.patch("/{content_id}")
def update(
    trip_id: str,
    content_id: str,
    body: ShortformUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    return service.update_shortform(
        db,
        trip_id,
        content_id,
        body.model_dump(exclude_unset=True),
    )

@router.delete("/{content_id}")
def delete(trip_id: str, content_id: str, db: Session = Depends(get_db)) -> dict:
    return service.delete_shortform(db, trip_id, content_id)
