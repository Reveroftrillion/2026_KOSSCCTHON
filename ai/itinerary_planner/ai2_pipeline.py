"""Backend entry point: assemble the current itinerary and a factual summary."""

import json
import sys
from typing import Any

if __package__:
    from .itinerary_generator import SAMPLE_INPUT_PATH, generate_itinerary
else:
    from itinerary_generator import SAMPLE_INPUT_PATH, generate_itinerary


def build_summary(itinerary: dict[str, Any]) -> str:
    """Summarize only generated region, date, time, stop count and categories."""
    schedule = itinerary["schedule"]
    categories = sorted({stop["category"] for stop in schedule})
    return (
        f"{itinerary['region']} 지역 {itinerary['date']} {itinerary['time_range']} 일정으로, "
        f"{len(schedule)}개 장소({', '.join(categories) or '없음'})로 구성되었습니다."
    )


def run_ai2_pipeline(
    conditions: dict[str, Any], profiles: list[dict[str, Any]] | None = None,
    place_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate once and add summary; preserve scores, coverage and reflection as returned."""
    itinerary = generate_itinerary(conditions, profiles=profiles, place_candidates=place_candidates)
    return {"summary": build_summary(itinerary), **itinerary}


def main() -> None:
    """Run the AI1 profiles and mock candidates demo with UTF-8 JSON output."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    conditions = json.loads(SAMPLE_INPUT_PATH.read_text(encoding="utf-8"))
    print(json.dumps(run_ai2_pipeline(conditions), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
