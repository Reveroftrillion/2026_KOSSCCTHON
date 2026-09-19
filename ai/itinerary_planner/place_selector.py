"""Greedy selection balancing group affinity and minimum user coverage."""

from typing import Any

GROUP_WEIGHT = 0.7
FAIRNESS_WEIGHT = 0.3
MAX_STOPS = 4


def select_places(
    scored_places: list[dict[str, Any]], user_ids: list[str], max_stops: int = MAX_STOPS,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Select without repetition and track each user's maximum selected-place score."""
    if type(max_stops) is not int or max_stops < 0:
        raise ValueError("max_stops는 0 이상의 정수여야 합니다.")
    coverage = {user: 0.0 for user in user_ids}
    remaining = {place["place_id"]: place for place in scored_places}
    if len(remaining) != len(scored_places):
        raise ValueError("place_id는 중복될 수 없습니다.")
    selected = []
    if not coverage:
        return selected, coverage
    while remaining and len(selected) < min(max_stops, MAX_STOPS):
        def objective(place_id: str) -> float:
            """Evaluate the minimum coverage after adding this candidate."""
            place = remaining[place_id]
            minimum = min(max(coverage[user], place["user_scores"][user]) for user in coverage)
            return GROUP_WEIGHT * place["group_score"] + FAIRNESS_WEIGHT * minimum

        # Sorted IDs give reproducible tie breaks independent of input ordering.
        best_id = max(sorted(remaining), key=objective)
        best = remaining.pop(best_id)
        selected.append(best)
        coverage = {user: max(score, best["user_scores"][user]) for user, score in coverage.items()}
    return selected, coverage
