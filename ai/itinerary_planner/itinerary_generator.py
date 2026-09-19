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


def calculate_preference_reflection(
    user_preferences: dict[str, list[str]], schedule: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Project-defined calculation rule (README does not specify a formula):
    for each user, the share of their own unique preference categories that
    appear at least once among the schedule's unique categories.

    reflection(user) = |user_categories ∩ schedule_categories| / |user_categories| * 100

    Uses only category set membership from user_preferences and schedule
    "category" values - no personal_preference_db scores, weights,
    thresholds, related_users, or reason. Duplicate categories in the
    schedule count once. A user with no recorded preference categories gets
    a percentage of None (undefined), never an assumed 0% or 100%."""
    schedule_categories = {
        item["category"] for item in schedule if item["category"] is not None
    }

    reflection: dict[str, dict[str, Any]] = {}
    for user, categories in user_preferences.items():
        user_categories = set(categories)
        matched_categories = sorted(user_categories & schedule_categories)
        total_categories = len(user_categories)
        percentage = (
            round(len(matched_categories) / total_categories * 100)
            if total_categories > 0
            else None
        )
        reflection[user] = {
            "matched_categories": matched_categories,
            "total_categories": total_categories,
            "preference_reflection_percent": percentage,
        }
    return reflection


def generate_itinerary(sample_input: dict[str, Any]) -> dict[str, Any]:
    """Combine the group preference profile with region/date/time and the
    user conditions into the itinerary structure, including each stop's
    reason and each user's preference reflection percentage."""
    analysis = analyze_preferences(sample_input["personal_preference_db"])
    balanced = balance_group_preferences(analysis, sample_input["group_saved_places"])

    schedule = generate_schedule(balanced["group_preference_profile"], sample_input["time"])
    conditions = classify_user_conditions(sample_input["user_conditions"])
    preference_reflection = calculate_preference_reflection(
        analysis["user_preferences"], schedule
    )

    return {
        "region": sample_input["region"],
        "date": sample_input["date"],
        "time_range": sample_input["time"],
        "schedule": schedule,
        "verifiable_conditions": conditions["verifiable"],
        "unverifiable_conditions": conditions["unverifiable"],
        "preference_reflection": preference_reflection,
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

    print("\n사용자별 취향 반영도 (README 공식이 아닌 프로젝트 계산 규칙)")
    for user, result in itinerary["preference_reflection"].items():
        matched = ", ".join(result["matched_categories"]) or "없음"
        if result["preference_reflection_percent"] is None:
            percent_text = "계산 불가 (취향 카테고리 없음)"
        else:
            percent_text = f"{result['preference_reflection_percent']}%"
        print(
            f"- {user}: {percent_text} "
            f"(일치 카테고리[{matched}] / 전체 취향 카테고리 {result['total_categories']}개)"
        )


if __name__ == "__main__":
    main()
