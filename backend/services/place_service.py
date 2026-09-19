"""Bounded Kakao Local search and explicit mock mode for AI2 candidates."""
import json
import math
import os
from pathlib import Path
import httpx
from backend.services.common import ServiceError

CATEGORY_MAP = {
    "카페": "cafe",
    "음식점": "food",
    "식당": "food",
    "미술관": "exhibition",
    "전시": "exhibition",
    "문화시설": "exhibition",

    "쇼핑": "shopping",
    "복합쇼핑몰": "shopping",
    "백화점": "shopping",
    "아울렛": "shopping",
    "쇼핑센터": "shopping",

    "공원": "outdoor",
    "관광명소": "sightseeing",
    "숙박": "accommodation",
    "술집": "nightlife",
    "주점": "nightlife",
    "스포츠": "activity",
}
NON_VISITABLE_SHOPPING_LABELS = {
    "통신판매",
    "인터넷쇼핑몰",
}
CATEGORIES = {"cafe", "food", "exhibition", "shopping", "outdoor", "activity", "sightseeing", "nightlife", "accommodation", "other"}
GROUP_CODES = {"CE7": "cafe", "FD6": "food", "CT1": "exhibition", "AT4": "sightseeing",
               "AD5": "accommodation", "MT1": "shopping"}
SEARCH_TERMS = {"cafe": "카페", "food": "맛집", "exhibition": "전시", "shopping": "쇼핑",
                "outdoor": "공원", "activity": "체험", "sightseeing": "관광명소",
                "nightlife": "술집", "accommodation": "숙박", "other": "가볼만한곳"}
TOP_CATEGORIES = 4
RESULTS_PER_QUERY = 5
MAX_CANDIDATES = 20
KAKAO_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def normalize_category(category: str) -> str:
    """Translate provider labels to the existing AI2 vocabulary."""
    value = category.strip().lower()
    return CATEGORY_MAP.get(value, value if value in CATEGORIES else "other")


def kakao_category(category_name: str, group_code: str = "") -> str:
    """Prefer specific category labels over broad Kakao group codes."""
    for label in reversed(category_name.split(">")):
        normalized = normalize_category(label)
        if normalized != "other":
            return normalized
    return GROUP_CODES.get(group_code, "other")


def search_queries(region: str, profiles: list[dict]) -> list[str]:
    """Rank category means (missing scores count as zero), with deterministic ties."""
    totals = {}
    for profile in profiles:
        for category, score in profile.get("category_preferences", {}).items():
            if category in SEARCH_TERMS and isinstance(score, (int, float)) and math.isfinite(score) and score > 0:
                totals[category] = totals.get(category, 0) + score / max(1, len(profiles))
    categories = sorted(totals, key=lambda category: (-totals[category], category))[:TOP_CATEGORIES]
    return [f"{region.strip()} {SEARCH_TERMS[category]}" for category in (categories or ["sightseeing"])]

def is_non_visitable_place(document: dict) -> bool:
    """Filter places that are not useful as offline itinerary stops."""
    category_name = document.get("category_name", "")

    labels = {
        label.strip()
        for label in category_name.split(">")
        if label.strip()
    }

    return bool(labels & NON_VISITABLE_SHOPPING_LABELS)

def normalize_kakao_place(document: dict) -> dict:
    """Use only provider facts for candidate keywords; do not infer mood or amenities."""
    place_id, name = document["id"], document["place_name"]
    if not isinstance(place_id, str) or not place_id or not isinstance(name, str) or not 0 < len(name) <= 200:
        raise ValueError("Invalid place identity")
    lat, lng = float(document["y"]), float(document["x"])
    if not math.isfinite(lat) or not math.isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
        raise ValueError("Invalid coordinates")
    labels = document.get("category_name", "")
    category = kakao_category(labels, document.get("category_group_code", ""))
    keywords = list(dict.fromkeys([category] + [label.strip() for label in labels.split(">") if label.strip()]))
    return {"place_id": place_id, "name": name, "category": category, "keywords": keywords, "lat": lat, "lng": lng}


def search_provider_places(region: str, profiles: list[dict]) -> list[dict]:
    """Search at most four first pages; errors never become mock results."""
    candidates = {}
    try:
        with httpx.Client(timeout=10.0, headers={"Authorization": "KakaoAK " + os.environ["KAKAO_REST_API_KEY"].strip()}) as client:
            for query in search_queries(region, profiles):
                response = client.get(KAKAO_URL, params={"query": query, "page": 1, "size": RESULTS_PER_QUERY})
                if response.status_code in (429, 503):
                    raise ServiceError(503, "Kakao 장소 검색을 일시적으로 사용할 수 없습니다.")
                response.raise_for_status()
                documents = response.json()["documents"]
                if not isinstance(documents, list):
                    raise ValueError("Invalid documents")
                for document in documents[:RESULTS_PER_QUERY]:
                    if is_non_visitable_place(document):
                        continue

                    place = normalize_kakao_place(document)
                    candidates.setdefault(place["place_id"], place)
                    if len(candidates) >= MAX_CANDIDATES:
                        return list(candidates.values())
    except ServiceError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        raise ServiceError(502, "Kakao 장소 검색에 실패했습니다. 연결 및 provider 설정을 확인해주세요.") from None
    if not candidates:
        raise ServiceError(503, "Kakao 검색 결과가 없습니다. 지역 또는 취향 조건을 확인해주세요.")
    return list(candidates.values())


def search_places(region: str, profiles: list[dict]) -> list[dict]:
    """Return explicit mock candidates without a key, or delegate to the provider hook."""
    if os.getenv("KAKAO_REST_API_KEY", "").strip():
        places = search_provider_places(region, profiles)
        source = "kakao"
    else:
        path = Path(__file__).resolve().parents[2] / "ai/itinerary_planner/sample_places.json"
        places = json.loads(path.read_text(encoding="utf-8"))
        source = "mock"
    return [{**place, "category": normalize_category(place["category"]), "source": source} for place in places]
