import json
from pathlib import Path

from ai.preference_analyzer import (
    PreferenceDB,
    process_youtube_url,
    export_all_preference_profiles,
)

from ai.itinerary_planner.ai2_pipeline import run_ai2_pipeline


# ============================================================
# 실제 Shorts 테스트 데이터
# ============================================================

TEST_USERS = {
    1: [
        # 카페 / 맛집 계열 Shorts를 넣어주세요.
        "https://www.youtube.com/shorts/p32NKLFW8Is",
        "https://www.youtube.com/shorts/cubmp0ecFdc",
        "https://www.youtube.com/shorts/KBzswudtwMU",
    ],

    2: [
        # 야외 / 관광 / 산책 계열 Shorts
        "https://www.youtube.com/shorts/mjUzQHe62Oo",
        "https://www.youtube.com/shorts/qYeZjIue8sA",
        "https://www.youtube.com/shorts/aaXM04vjj0k",
    ],

    3: [
        # 전시 / 쇼핑 / 사진 계열 Shorts
        "https://www.youtube.com/shorts/_notwElp77E",
        "https://www.youtube.com/shorts/KMuSaY0LPj0",
        "https://www.youtube.com/shorts/ahtAI4VlmOA",
    ],
}


# ============================================================
# 여행 조건
# ============================================================

CONDITIONS = {
    "region": "성수",
    "date": "토요일",
    "time": "13:00 ~ 20:00",
    "user_conditions": [],
}


# ============================================================
# 현재는 Backend Map API가 없으므로 Mock 장소 사용
# ============================================================

SAMPLE_PLACES_PATH = (
    Path(__file__).parent
    / "itinerary_planner"
    / "sample_places.json"
)


def print_json(title: str, data) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    # 프로그램 실행마다 새로운 임시 Preference DB 생성
    preference_db = PreferenceDB()

    successful_contents = 0
    failed_contents = 0

    print("\nTripClip AI End-to-End Test")
    print("=" * 70)

    # ========================================================
    # AI1
    # Shorts → Metadata → Claude → Preference DB
    # ========================================================

    for user_id, urls in TEST_USERS.items():

        print("\n" + "#" * 70)
        print(f"USER {user_id} 분석 시작")
        print("#" * 70)

        for index, url in enumerate(urls, start=1):

            # placeholder URL을 실수로 남겨도 전체 테스트가 죽지 않게 함
            if not url.startswith("http"):
                print(
                    f"\n[SKIP] User {user_id} Content {index}"
                    f" - 실제 URL이 아닙니다."
                )
                continue

            print(
                f"\n[PROCESS] User {user_id}"
                f" - Content {index}"
            )

            print(f"URL: {url}")

            try:
                result = process_youtube_url(
                    user_id=user_id,
                    url=url,
                    preference_db=preference_db,
                )

                successful_contents += 1

                analysis = result["analysis"]

                print("\n분석 성공")
                print(
                    json.dumps(
                        analysis,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

                print("\n현재 누적 Preference:")
                print(
                    json.dumps(
                        result["preference_profile"],
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            except Exception as error:
                failed_contents += 1

                print("\n분석 실패")
                print(
                    f"{type(error).__name__}: {error}"
                )

    # ========================================================
    # AI1 최종 결과
    # ========================================================

    profiles = export_all_preference_profiles(
        preference_db
    )

    print_json(
        "AI1 FINAL PREFERENCE PROFILES",
        profiles,
    )

    # ========================================================
    # AI2 장소 후보
    # ========================================================

    with SAMPLE_PLACES_PATH.open(
        encoding="utf-8"
    ) as file:
        places = json.load(file)

    print_json(
        "PLACE CANDIDATES",
        places,
    )

    # ========================================================
    # AI2
    # 개인 취향 → 그룹 취향 → 장소 점수 → Fairness → 일정
    # ========================================================

    if not profiles:
        print("\nPreference Profile이 없습니다.")
        print("AI2 테스트를 진행할 수 없습니다.")
        return

    result = run_ai2_pipeline(
        conditions=CONDITIONS,
        profiles=profiles,
        place_candidates=places,
    )

    # ========================================================
    # 최종 결과
    # ========================================================

    print_json(
        "FINAL AI ITINERARY",
        result,
    )

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"성공한 Shorts: {successful_contents}")
    print(f"실패한 Shorts: {failed_contents}")
    print(f"생성된 사용자 Profile: {len(profiles)}")
    print(f"생성된 일정 장소: {len(result['schedule'])}")

    print("\nPreference Coverage:")

    for user_id, score in result[
        "preference_coverage"
    ].items():
        print(
            f"User {user_id}: "
            f"{score:.3f}"
        )

    print("\nPreference Reflection:")

    for user_id, reflection in result[
        "preference_reflection"
    ].items():

        percent = reflection[
            "preference_reflection_percent"
        ]

        print(
            f"User {user_id}: "
            f"{percent}% "
            f"{reflection['matched_categories']}"
        )

    print("\nEnd-to-End AI Test Complete.")


if __name__ == "__main__":
    main()