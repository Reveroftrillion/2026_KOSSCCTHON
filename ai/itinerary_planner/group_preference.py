"""Analyze individual and group preferences from the AI 2 sample input."""

import json
import argparse
import math
from pathlib import Path
from typing import Any


SAMPLE_INPUT_PATH = Path(__file__).with_name("sample_input.json")


def build_group_preferences(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Preserve AI1 scores and average each preference over all users, including zeros."""
    if not isinstance(profiles, list):
        raise ValueError("AI1 프로필은 사용자 객체의 배열이어야 합니다.")
    users: dict[str, Any] = {}
    fields = ("category_preferences", "keyword_preferences")
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("각 프로필은 객체여야 합니다.")
        user_id = profile.get("user_id")
        if type(user_id) is not int or user_id <= 0 or str(user_id) in users:
            raise ValueError("user_id는 중복 없는 양의 정수여야 합니다.")
        user = {}
        for field in fields:
            scores = profile.get(field)
            if not isinstance(scores, dict):
                raise ValueError(f"{field}는 취향 이름과 점수의 객체여야 합니다.")
            for name, score in scores.items():
                if (not isinstance(name, str) or not name.strip()
                        or type(score) not in (int, float) or not math.isfinite(score)
                        or not 0 <= score <= 1):
                    raise ValueError(f"{field}의 점수는 0~1 범위의 유한한 숫자여야 합니다.")
            user[field] = dict(scores)
        users[str(user_id)] = user
    result: dict[str, Any] = {"users": users}
    for field in fields:
        names = sorted({name for user in users.values() for name in user[field]})
        result[f"group_{field}"] = {
            name: round(math.fsum(user[field].get(name, 0) for user in users.values()) / len(users), 3)
            for name in names
        }
    return result


def load_preference_profiles(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate the same AI1 array accepted by build_group_preferences."""
    with Path(path).open(encoding="utf-8") as input_file:
        profiles = json.load(input_file)
    build_group_preferences(profiles)
    return profiles


def preference_categories(preferences: Any) -> set[str]:
    """Return category names without calculating or changing preference scores."""
    if isinstance(preferences, dict):
        return set(preferences)
    if isinstance(preferences, list):
        return set(preferences)
    raise ValueError("각 사용자의 취향은 객체 또는 목록이어야 합니다.")


def analyze_preferences(personal_preference_db: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze common preferences, individual-only preferences, and differences."""
    if isinstance(personal_preference_db, list):
        scored = build_group_preferences(personal_preference_db)
        legacy = analyze_preferences({
            user: profile["category_preferences"] for user, profile in scored["users"].items()
        })
        return {**legacy, **scored}
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

    result = {
        "group_preference_profile": group_preference_profile,
        "common_preferences": analysis["common_preferences"],
        "individual_only_preferences": analysis["individual_only_preferences"],
        "preference_differences": analysis["preference_differences"],
    }
    if "users" in analysis:
        # Keep the scored contract alongside legacy itinerary fields.
        result.update({key: analysis[key] for key in (
            "users", "group_category_preferences", "group_keyword_preferences",
        )})
    return result


def main() -> None:
    """Run the legacy sample by default, or aggregate an AI1 JSON file."""
    parser = argparse.ArgumentParser(description="AI1 프로필 연결 또는 기존 AI2 샘플 실행")
    parser.add_argument("profiles", nargs="?", help="AI1 사용자 프로필 JSON 배열 파일")
    args = parser.parse_args()
    if args.profiles:
        result = build_group_preferences(load_preference_profiles(args.profiles))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
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
