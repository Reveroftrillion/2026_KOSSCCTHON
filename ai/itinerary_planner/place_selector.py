"""Greedy selection balancing group affinity and minimum user coverage."""

from typing import Any

GROUP_WEIGHT = 0.4
COVERAGE_GAIN_WEIGHT = 0.4
CATEGORY_GAIN_WEIGHT = 0.2
MAX_STOPS = 4


def select_places(
    scored_places: list[dict[str, Any]],
    user_ids: list[str],
    max_stops: int = MAX_STOPS,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Select places using group affinity and marginal preference coverage."""
    if type(max_stops) is not int or max_stops < 0:
        raise ValueError("max_stops는 0 이상의 정수여야 합니다.")

    coverage = {user: 0.0 for user in user_ids}

    # 각 사용자가 일정에서 이미 반영받은 선호 category를 기록한다.
    covered_categories: dict[str, set[str]] = {
        user: set() for user in user_ids
    }

    remaining = {
        place["place_id"]: place
        for place in scored_places
    }

    if len(remaining) != len(scored_places):
        raise ValueError("place_id는 중복될 수 없습니다.")

    selected = []

    if not coverage:
        return selected, coverage

    while remaining and len(selected) < min(max_stops, MAX_STOPS):

        def objective(place_id: str) -> float:
            place = remaining[place_id]

            # 이 장소가 선택됐을 때 각 사용자의 기존 coverage가
            # 실제로 얼마나 증가하는지 계산한다.
            coverage_gains = []

            for user in coverage:
                current = coverage[user]
                candidate = place["user_scores"][user]

                coverage_gains.append(
                    max(current, candidate) - current
                )

            average_coverage_gain = (
                sum(coverage_gains) / len(coverage_gains)
                if coverage_gains
                else 0.0
            )

            # 아직 일정에 반영되지 않은 사용자의 category 취향을
            # 새로 만족시키는 경우 보상한다.
            #
            # 단순히 "새 category라서" 보너스를 주는 것이 아니라
            # 실제 해당 사용자의 category preference가 있는 경우만 반영한다.
            unmet_category_scores = []

            score_details = place.get("score_details", {})

            for user in coverage:
                details = score_details.get(user)

                # 기존 테스트처럼 score_details가 없는 scored place도
                # select_places()에서 계속 사용할 수 있게 한다.
                if not details:
                    continue

                category_score = details.get("category_score", 0.0)

                if (
                    category_score > 0
                    and place.get("category") not in covered_categories[user]
                ):
                    unmet_category_scores.append(category_score)

            # 여러 사용자 중 아직 충족되지 않은 가장 강한 category preference
            # 하나를 기준으로 category gain을 계산한다.
            category_gain = (
                max(unmet_category_scores)
                if unmet_category_scores
                else 0.0
            )

            return (
                GROUP_WEIGHT * place["group_score"]
                + COVERAGE_GAIN_WEIGHT * average_coverage_gain
                + CATEGORY_GAIN_WEIGHT * category_gain
            )

        best_id = max(
            sorted(remaining),
            key=objective,
        )

        best = remaining.pop(best_id)
        selected.append(best)

        # 사용자별 maximum coverage 갱신
        coverage = {
            user: max(
                coverage[user],
                best["user_scores"][user],
            )
            for user in coverage
        }

        # 실제 category preference가 있었던 사용자에게만
        # 해당 category가 반영됐다고 기록한다.
        best_score_details = best.get("score_details", {})

        for user in coverage:
            details = best_score_details.get(user)

            if not details:
                continue

            if details.get("category_score", 0.0) > 0:
                category = best.get("category")

                if category:
                    covered_categories[user].add(category)

    return selected, coverage
