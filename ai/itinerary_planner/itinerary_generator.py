"""Build a scored, balanced itinerary from AI1 profiles and mock place candidates."""

import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__:
    from .group_preference import build_group_preferences, load_preference_profiles
    from .place_scoring import build_reason, related_users, score_places
    from .place_selector import select_places
else:
    from group_preference import build_group_preferences, load_preference_profiles
    from place_scoring import build_reason, related_users, score_places
    from place_selector import select_places

SAMPLE_INPUT_PATH = Path(__file__).with_name("sample_input.json")
SAMPLE_PLACES_PATH = Path(__file__).with_name("sample_places.json")
SAMPLE_PROFILES_PATH = Path(__file__).parents[1] / "preference_analyzer/sample_group_preferences.json"


def parse_time_range(time_range: str) -> tuple[str, str]:
    """Validate a same-day HH:MM ~ HH:MM range."""
    parts = [part.strip() for part in time_range.split("~")]
    if len(parts) != 2 or any(not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", part) for part in parts):
        raise ValueError("시간 범위는 HH:MM ~ HH:MM 형식이어야 합니다.")
    if parts[0] >= parts[1]:
        raise ValueError("같은 날의 종료 시간이 시작 시간보다 늦어야 합니다.")
    return parts[0], parts[1]


def _to_minutes(hhmm: str) -> int:
    """Convert a validated time to minutes since midnight."""
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


def generate_schedule(selected_places: list[dict[str, Any]], time_range: str) -> list[dict[str, Any]]:
    """Evenly space selected stops; category always comes from the place itself."""
    start, end = map(_to_minutes, parse_time_range(time_range))
    if len(selected_places) > end - start:
        raise ValueError("선택한 장소 수만큼 분 단위 시간 배치가 가능한 범위가 필요합니다.")
    schedule = []
    for index, place in enumerate(selected_places):
        minutes = start + (end - start) * index // len(selected_places)
        users = related_users(place)
        schedule.append({
            "time": f"{minutes // 60:02d}:{minutes % 60:02d}",
            "place_id": place["place_id"], "place": place["name"], "category": place["category"],
            "user_scores": {user: round(score, 3) for user, score in place["user_scores"].items()},
            "group_score": round(place["group_score"], 3), "related_users": users,
            "reason": build_reason(place, users),
        })
    return schedule


def classify_user_conditions(user_conditions: list[str]) -> dict[str, list[str]]:
    """Price, meal type and opening hours remain unverifiable with current data."""
    return {"verifiable": [], "unverifiable": list(user_conditions)}


def generate_itinerary(
    sample_input: dict[str, Any], profiles: list[dict[str, Any]] | None = None,
    place_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine trip conditions, AI1 profiles and candidates; omitted inputs use demo files."""
    if profiles is None:
        profiles = load_preference_profiles(SAMPLE_PROFILES_PATH)
    if place_candidates is None:
        place_candidates = json.loads(SAMPLE_PLACES_PATH.read_text(encoding="utf-8"))
    group = build_group_preferences(profiles)
    scored = score_places(group, place_candidates)
    selected, coverage = select_places(scored, list(group["users"]))
    conditions = classify_user_conditions(sample_input.get("user_conditions", []))
    return {
        "region": sample_input["region"], "date": sample_input["date"], "time_range": sample_input["time"],
        "schedule": generate_schedule(selected, sample_input["time"]),
        "preference_coverage": {user: round(score, 3) for user, score in coverage.items()},
        "verifiable_conditions": conditions["verifiable"],
        "unverifiable_conditions": conditions["unverifiable"],
    }


def main() -> None:
    """Run the full AI1 sample → candidate scoring → balanced itinerary demo."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sample_input = json.loads(SAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
    print(json.dumps(generate_itinerary(sample_input), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
