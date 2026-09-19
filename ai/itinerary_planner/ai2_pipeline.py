"""Entry point that runs the full AI2 pipeline (README section 6) against a
single sample_input.json, reusing the already-verified functions in
group_preference.py and itinerary_generator.py:

1. Personal and group preference analysis
2. group_preference_profile construction
3. Basic schedule generation
4. Per-stop reason
5. Per-user preference reflection
6. Final AI2 result assembly (summary + schedule)

No new preference score, weight, threshold, place, or recommendation logic
is introduced here - this module only calls existing functions and packages
their results."""

import json
from pathlib import Path
from typing import Any

from itinerary_generator import generate_itinerary

SAMPLE_INPUT_PATH = Path(__file__).with_name("sample_input.json")


def build_summary(itinerary: dict[str, Any]) -> str:
    """Summarize the already-generated itinerary. Introduces no new
    recommendation judgment - only restates region/date/time and the
    schedule's own place count and categories."""
    schedule = itinerary["schedule"]
    categories = sorted(
        {item["category"] for item in schedule if item["category"] is not None}
    )
    category_text = ", ".join(categories) if categories else "없음"
    return (
        f"{itinerary['region']} 지역 {itinerary['date']} {itinerary['time_range']} 일정으로, "
        f"{len(schedule)}개 장소({category_text} 카테고리)로 구성되었습니다."
    )


def run_ai2_pipeline(sample_input: dict[str, Any]) -> dict[str, Any]:
    """Run the AI2 pipeline end to end and assemble the final AI2 result.

    generate_itinerary() already performs steps 1-5 (preference analysis,
    group_preference_profile construction, schedule generation with reason,
    and preference reflection) using the existing, verified functions from
    group_preference.py and itinerary_generator.py. This function only adds
    the summary and packages the final result (step 6)."""
    itinerary = generate_itinerary(sample_input)

    return {
        "summary": build_summary(itinerary),
        "schedule": itinerary["schedule"],
        "preference_reflection": itinerary["preference_reflection"],
        "region": itinerary["region"],
        "date": itinerary["date"],
        "time_range": itinerary["time_range"],
        "verifiable_conditions": itinerary["verifiable_conditions"],
        "unverifiable_conditions": itinerary["unverifiable_conditions"],
    }


def main() -> None:
    with SAMPLE_INPUT_PATH.open(encoding="utf-8") as input_file:
        sample_input = json.load(input_file)

    result = run_ai2_pipeline(sample_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
