"""Generate the basic group itinerary schedule from the group preference
profile and the trip conditions in the AI 2 sample input."""

import json
from pathlib import Path
from typing import Any

from group_preference import analyze_preferences, balance_group_preferences

SAMPLE_INPUT_PATH = Path(__file__).with_name("sample_input.json")


def parse_time_range(time_range: str) -> tuple[str, str]:
    """Split a "13:00 ~ 20:00" style range into its start and end strings."""
    start, end = (part.strip() for part in time_range.split("~"))
    return start, end


def _to_minutes(hhmm: str) -> int:
    hours, minutes = (int(part) for part in hhmm.split(":"))
    return hours * 60 + minutes


def _to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def build_reason(
    category: str | None, group_preference_profile: dict[str, dict[str, Any]]
) -> str:
    """Explain a stop using only categories already recorded in
    group_preference_profile: every member whose own preference categories
    include this stop's category is named as the basis for including it."""
    if category is not None:
        interested_users = [
            user
            for user, profile in group_preference_profile.items()
            if category in profile["categories"]
        ]
        if interested_users:
            names = ", ".join(interested_users)
            return f"{names}의 {category} 취향을 반영했습니다."
    return "현재 데이터로 확인할 수 있는 취향 근거가 없습니다."


def generate_schedule(
    group_preference_profile: dict[str, dict[str, Any]], time_range: str
) -> list[dict[str, Any]]:
    """Build the basic schedule from each member's own saved places only.

    Each stop is tagged with one of the categories already recorded for the
    member who saved that place (paired by list position, cycling through
    the member's categories). No new preference score, weight, or threshold
    is introduced, and no place outside group_saved_places is used."""
    start_minutes, end_minutes = (
        _to_minutes(value) for value in parse_time_range(time_range)
    )

    stops: list[dict[str, Any]] = []
    for user, profile in group_preference_profile.items():
        categories = profile["categories"]
        for index, place in enumerate(profile["saved_places"]):
            category = categories[index % len(categories)] if categories else None
            stops.append({"user": user, "place": place, "category": category})

    if not stops:
        return []

    interval = (end_minutes - start_minutes) // len(stops)
    schedule = []
    for index, stop in enumerate(stops):
        schedule.append(
            {
                "time": _to_hhmm(start_minutes + interval * index),
                "place": stop["place"],
                "category": stop["category"],
                "related_users": [stop["user"]],
                "reason": build_reason(stop["category"], group_preference_profile),
            }
        )
    return schedule


def classify_user_conditions(user_conditions: list[str]) -> dict[str, list[str]]:
    """Split user_conditions into what the current data can verify and what
    it cannot. group_saved_places only holds plain place names, with no
    price, operating-hours, or meal-type information, so none of the given
    conditions can actually be checked against it yet. Every condition is
    reported as unverifiable instead of being assumed satisfied."""
    return {
        "verifiable": [],
        "unverifiable": list(user_conditions),
    }


def generate_itinerary(sample_input: dict[str, Any]) -> dict[str, Any]:
    """Combine the group preference profile with region/date/time and the
    user conditions into the basic itinerary structure. reason and
    preference-reflection percentages are left for a later step."""
    analysis = analyze_preferences(sample_input["personal_preference_db"])
    balanced = balance_group_preferences(analysis, sample_input["group_saved_places"])

    schedule = generate_schedule(balanced["group_preference_profile"], sample_input["time"])
    conditions = classify_user_conditions(sample_input["user_conditions"])

    return {
        "region": sample_input["region"],
        "date": sample_input["date"],
        "time_range": sample_input["time"],
        "schedule": schedule,
        "verifiable_conditions": conditions["verifiable"],
        "unverifiable_conditions": conditions["unverifiable"],
    }


def main() -> None:
    with SAMPLE_INPUT_PATH.open(encoding="utf-8") as input_file:
        sample_input = json.load(input_file)

    itinerary = generate_itinerary(sample_input)

    print(f"지역: {itinerary['region']}")
    print(f"날짜: {itinerary['date']}")
    print(f"시간: {itinerary['time_range']}")

    print("\n기본 일정 (schedule)")
    for item in itinerary["schedule"]:
        related = ", ".join(item["related_users"])
        print(f"{item['time']} {item['place']} ({item['category']}) - {related}")
        print(f"  → {item['reason']}")

    print("\n현재 데이터로 검증할 수 없는 사용자 조건")
    for condition in itinerary["unverifiable_conditions"]:
        print(f"- {condition} (group_saved_places에 관련 정보 없음)")


if __name__ == "__main__":
    main()
