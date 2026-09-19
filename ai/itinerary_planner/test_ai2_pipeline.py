"""Selective feature port regression tests against the integration pipeline."""

import json
import unittest
from unittest.mock import patch

from ai.itinerary_planner.ai2_pipeline import build_summary, run_ai2_pipeline
from ai.itinerary_planner.itinerary_generator import calculate_preference_reflection, generate_itinerary


class PipelineTests(unittest.TestCase):
    """Keep coverage/scoring intact while adding category reflection and entry point."""

    def setUp(self) -> None:
        """Use deliberately distinct profile scores and real candidate categories."""
        self.conditions = {"region": "성수", "date": "토요일", "time": "13:00 ~ 20:00", "user_conditions": []}
        self.profiles = [{"user_id": 1, "category_preferences": {"cafe": .5, "food": .25, "exhibition": .25}, "keyword_preferences": {"photo": .5}}]
        self.places = [
            {"place_id": "p1", "name": "카페", "category": "cafe", "keywords": ["photo"]},
            {"place_id": "p2", "name": "전시", "category": "exhibition", "keywords": []},
        ]

    def test_sample_coverage_unchanged(self) -> None:
        """Preserve the established fairness-selected sample sequence and scores."""
        result = run_ai2_pipeline(self.conditions)
        self.assertEqual(result["preference_coverage"], {"1": .467, "2": .55, "3": .533})
        self.assertEqual([stop["place_id"] for stop in result["schedule"]], ["p1", "p3", "p2", "p8"])
        self.assertEqual(result["schedule"][0]["user_scores"]["1"], .467)

    def test_reflection_and_independent_coverage(self) -> None:
        """Two of three categories yield 67%, independently of affinity magnitude."""
        result = run_ai2_pipeline(self.conditions, self.profiles, self.places)
        self.assertEqual(result["preference_reflection"]["1"], {
            "matched_categories": ["cafe", "exhibition"], "total_categories": 3,
            "preference_reflection_percent": 67,
        })
        self.assertEqual(result["preference_coverage"]["1"], .5)

    def test_category_keys_and_denominator(self) -> None:
        """Use profile keys, even explicit zeros; unrelated schedule categories add nothing."""
        users = {"1": {"category_preferences": {"cafe": 0, "food": 1}, "keyword_preferences": {"outdoor": 1}}}
        result = calculate_preference_reflection(users, [{"category": "cafe"}, {"category": "cafe"}, {"category": "outdoor"}])
        self.assertEqual(result["1"], {"matched_categories": ["cafe"], "total_categories": 2, "preference_reflection_percent": 50})

    def test_empty_preferences(self) -> None:
        """No recorded categories yields null, not an assumed percentage."""
        self.profiles[0]["category_preferences"] = {}
        result = run_ai2_pipeline(self.conditions, self.profiles, self.places)
        self.assertIsNone(result["preference_reflection"]["1"]["preference_reflection_percent"])
        self.assertEqual(result["preference_coverage"]["1"], .2)

    def test_empty_schedule(self) -> None:
        """Explicit empty candidates are not replaced with demo data."""
        result = run_ai2_pipeline(self.conditions, self.profiles, [])
        self.assertEqual(result["schedule"], [])
        self.assertEqual(result["preference_reflection"]["1"]["preference_reflection_percent"], 0)
        self.assertIn("0개 장소(없음)", result["summary"])

    def test_delegation_once(self) -> None:
        """Forward input objects and preserve every field from the existing generator."""
        itinerary = generate_itinerary(self.conditions, self.profiles, self.places)
        with patch("ai.itinerary_planner.ai2_pipeline.generate_itinerary", return_value=itinerary) as generate:
            result = run_ai2_pipeline(self.conditions, self.profiles, self.places)
        generate.assert_called_once_with(self.conditions, profiles=self.profiles, place_candidates=self.places)
        self.assertEqual({key: result[key] for key in itinerary}, itinerary)
        self.assertIs(result["schedule"], itinerary["schedule"])

    def test_summary_from_result_only(self) -> None:
        """Summarize provided facts without deriving new recommendations."""
        summary = build_summary({"region": "지역", "date": "날짜", "time_range": "시간", "schedule": [{"category": "food"}, {"category": "food"}, {"category": "cafe"}]})
        self.assertEqual(summary, "지역 지역 날짜 시간 일정으로, 3개 장소(cafe, food)로 구성되었습니다.")

    def test_candidate_categories_reason_and_json(self) -> None:
        """Keep real categories and detailed evidence-based reasons in JSON output."""
        result = run_ai2_pipeline(self.conditions, self.profiles, self.places)
        self.assertEqual([stop["category"] for stop in result["schedule"]], ["cafe", "exhibition"])
        self.assertIn("photo", result["schedule"][0]["reason"])
        self.assertEqual(result["schedule"][0]["related_users"], [1])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)


if __name__ == "__main__":
    unittest.main()
