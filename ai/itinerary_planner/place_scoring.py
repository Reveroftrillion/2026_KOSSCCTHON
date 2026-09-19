"""Deterministic place affinity scores; no network or LLM calls."""

import math
from typing import Any

CATEGORY_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4


def score_user_place(user: dict[str, Any], place: dict[str, Any]) -> dict[str, Any]:
    """Average matching keyword scores only, then combine with category affinity."""
    category_score = user["category_preferences"].get(place["category"], 0.0)
    matched = sorted(set(place["keywords"]) & user["keyword_preferences"].keys())
    keyword_score = math.fsum(user["keyword_preferences"][key] for key in matched) / len(matched) if matched else 0.0
    return {
        "category_score": category_score,
        "keyword_score": keyword_score,
        "matched_keywords": matched,
        "user_place_score": CATEGORY_WEIGHT * category_score + KEYWORD_WEIGHT * keyword_score,
    }


def score_places(group: dict[str, Any], places: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate candidate identities and preserve their real categories while scoring."""
    scored = []
    seen = set()
    for place in places:
        if not isinstance(place, dict) or any(
            not isinstance(place.get(key), str) or not place[key].strip()
            for key in ("place_id", "name", "category")
        ):
            raise ValueError("장소에는 place_id, name, category 문자열이 필요합니다.")
        if place["place_id"] in seen:
            raise ValueError("place_id는 중복될 수 없습니다.")
        seen.add(place["place_id"])
        keywords = place.get("keywords", [])
        if not isinstance(keywords, list) or any(not isinstance(key, str) or not key.strip() for key in keywords):
            raise ValueError("장소 keywords는 문자열 배열이어야 합니다.")
        normalized = {**place, "keywords": list(dict.fromkeys(keywords))}
        details = {user_id: score_user_place(user, normalized) for user_id, user in group["users"].items()}
        scores = {user_id: item["user_place_score"] for user_id, item in details.items()}
        scored.append({**normalized, "user_scores": scores, "score_details": details,
                       "group_score": math.fsum(scores.values()) / len(scores) if scores else 0.0})
    return scored


def related_users(place: dict[str, Any]) -> list[int]:
    """Identify users at or above the mean; keep the highest user as a fallback."""
    scores = place["user_scores"]
    users = [int(user) for user, score in scores.items() if score >= place["group_score"]]
    if not users and scores:
        users = [int(max(scores, key=scores.get))]
    return sorted(users)


def build_reason(place: dict[str, Any], users: list[int]) -> str:
    """Explain positive category/keyword matches without inventing preference evidence."""
    parts = []
    for user in users:
        details = place["score_details"][str(user)]
        matches = []
        if details["category_score"] > 0:
            matches.append(f"{place['category']} 카테고리")
        if details["keyword_score"] > 0:
            matches.append("/".join(details["matched_keywords"]) + " 키워드")
        if matches:
            parts.append(f"{user}번 사용자의 " + ", ".join(matches) + " 취향")
    return " 및 ".join(parts) + "을 반영한 장소입니다." if parts else "저장된 취향과 일치하는 긍정적 근거가 없는 후보입니다."
