"""Analyze individual and group preferences from the AI 2 sample input."""

import json
from pathlib import Path
from typing import Any


SAMPLE_INPUT_PATH = Path(__file__).with_name("sample_input.json")


def preference_categories(preferences: Any) -> set[str]:
    """Return category names without calculating or changing preference scores."""
    if isinstance(preferences, dict):
        return set(preferences)
    if isinstance(preferences, list):
        return set(preferences)
    raise ValueError("각 사용자의 취향은 객체 또는 목록이어야 합니다.")


def analyze_preferences(personal_preference_db: dict[str, Any]) -> dict[str, Any]:
    """Analyze common preferences, individual-only preferences, and differences."""
    categories_by_user = {
        user: preference_categories(preferences)
        for user, preferences in personal_preference_db.items()
    }

    if not categories_by_user:
        return {
            "user_preferences": {},
            "common_preferences": [],
            "individual_only_preferences": {},
            "preference_differences": {},
        }

    all_categories = set().union(*categories_by_user.values())
    common_preferences = {
        category
        for category in all_categories
        if sum(category in categories for categories in categories_by_user.values()) >= 2
    }
    individual_only_preferences = {
        user: sorted(
            category
            for category in categories
            if sum(category in other for other in categories_by_user.values()) == 1
        )
        for user, categories in categories_by_user.items()
    }
    preference_differences = {
        user: sorted(all_categories - categories)
        for user, categories in categories_by_user.items()
    }

    return {
        "user_preferences": {
            user: sorted(categories)
            for user, categories in categories_by_user.items()
        },
        "common_preferences": sorted(common_preferences),
        "individual_only_preferences": individual_only_preferences,
        "preference_differences": preference_differences,
    }


def balance_group_preferences(
    analysis: dict[str, Any], group_saved_places: dict[str, list[str]]
) -> dict[str, Any]:
    """Structure the existing group preference analysis, together with each
    member's saved places, into a group_preference_profile for the itinerary
    generation step to consume. Does not change or re-derive the analysis."""
    group_preference_profile = {
        user: {
            "categories": categories,
            "saved_places": group_saved_places.get(user, []),
        }
        for user, categories in analysis["user_preferences"].items()
    }

    return {
        "group_preference_profile": group_preference_profile,
        "common_preferences": analysis["common_preferences"],
        "individual_only_preferences": analysis["individual_only_preferences"],
        "preference_differences": analysis["preference_differences"],
    }


def main() -> None:
    with SAMPLE_INPUT_PATH.open(encoding="utf-8") as input_file:
        sample_input = json.load(input_file)

    analysis = analyze_preferences(sample_input["personal_preference_db"])
    balanced = balance_group_preferences(analysis, sample_input["group_saved_places"])

    print("사용자별 취향")
    for user, categories in analysis["user_preferences"].items():
        print(f"- {user}: {', '.join(categories)}")

    print("\n그룹 공통 취향")
    print(", ".join(analysis["common_preferences"]) or "없음")

    print("\n특정 사용자만 선호하는 활동")
    for user, categories in analysis["individual_only_preferences"].items():
        print(f"- {user}: {', '.join(categories) or '없음'}")

    print("\n구성원 간 취향 차이")
    for user, categories in analysis["preference_differences"].items():
        print(f"- {user}에게 없는 다른 구성원의 취향: {', '.join(categories) or '없음'}")

    print("\n그룹 취향 프로필 (일정 생성 단계에서 사용할 정보)")
    for user, profile in balanced["group_preference_profile"].items():
        categories = ", ".join(profile["categories"]) or "없음"
        places = ", ".join(profile["saved_places"]) or "없음"
        print(f"- {user}: 취향[{categories}] / 저장 장소[{places}]")


if __name__ == "__main__":
    main()
