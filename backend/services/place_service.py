"""Mock candidates now; a separate provider boundary for future Maps integration."""
import json
import os
from pathlib import Path
from backend.services.common import ServiceError

CATEGORY_MAP = {"카페": "cafe", "음식점": "food", "식당": "food", "미술관": "exhibition", "전시": "exhibition",
                "쇼핑": "shopping", "공원": "outdoor", "관광명소": "sightseeing", "숙박": "accommodation"}
CATEGORIES = {"cafe", "food", "exhibition", "shopping", "outdoor", "activity", "sightseeing", "nightlife", "accommodation", "other"}


def normalize_category(category: str) -> str:
    """Translate provider labels to the existing AI2 vocabulary."""
    value = category.strip().lower()
    return CATEGORY_MAP.get(value, value if value in CATEGORIES else "other")


def search_provider_places(region: str, profiles: list[dict]) -> list[dict]:
    """Reserved provider hook; never silently claim mock data is real Maps data."""
    raise ServiceError(503, "실제 지도 provider는 아직 구현되지 않았습니다. KAKAO_REST_API_KEY를 해제하면 mock 후보를 사용합니다.")


def search_places(region: str, profiles: list[dict]) -> list[dict]:
    """Return explicit mock candidates without a key, or delegate to the provider hook."""
    if os.getenv("KAKAO_REST_API_KEY", "").strip():
        places = search_provider_places(region, profiles)
        source = "provider"
    else:
        path = Path(__file__).resolve().parents[2] / "ai/itinerary_planner/sample_places.json"
        places = json.loads(path.read_text(encoding="utf-8"))
        source = "mock"
    return [{**place, "category": normalize_category(place["category"]), "source": source} for place in places]
