"""Deterministic scoring, fairness, candidate identity and schedule acceptance tests."""

import json
from pathlib import Path
import unittest

from ai.itinerary_planner.group_preference import build_group_preferences, load_preference_profiles
from ai.itinerary_planner.itinerary_generator import generate_itinerary, generate_schedule, SAMPLE_PROFILES_PATH, SAMPLE_PLACES_PATH
from ai.itinerary_planner.place_scoring import score_user_place, score_places, related_users, build_reason
from ai.itinerary_planner.place_selector import select_places, MAX_STOPS


class ItineraryTests(unittest.TestCase):
    """Verify arithmetic and output without any external API calls."""

    def setUp(self) -> None:
        """Create category and partial-keyword preferences for exact arithmetic."""
        self.profiles = [
            {"user_id": 1, "category_preferences": {"cafe": .5}, "keyword_preferences": {"dessert": .5, "photo": .25, "date": .5}},
            {"user_id": 2, "category_preferences": {"outdoor": 1}, "keyword_preferences": {}},
        ]
        self.group = build_group_preferences(self.profiles)
        self.place = {"place_id": "p1", "name": "카페", "category": "cafe", "keywords": ["dessert", "photo", "date"]}
        self.conditions = {"region": "성수", "date": "토요일", "time": "13:00 ~ 20:00", "user_conditions": ["저녁 식사 포함"]}

    def test_category_score(self) -> None:
        """Read the real candidate category's score."""
        self.assertEqual(score_user_place(self.group["users"]["1"], self.place)["category_score"], .5)

    def test_keyword_score(self) -> None:
        """Use matching keywords only; duplicates never change the mean."""
        place = {**self.place, "keywords": ["dessert", "photo", "missing", "photo"]}
        self.assertEqual(score_user_place(self.group["users"]["1"], place)["keyword_score"], .375)
        self.assertEqual(score_user_place(self.group["users"]["2"], place)["keyword_score"], 0)

    def test_user_score(self) -> None:
        """Compute the required 0.6 category + 0.4 keyword combination."""
        score = score_user_place(self.group["users"]["1"], self.place)["user_place_score"]
        self.assertAlmostEqual(score, .5 * .6 + (1.25 / 3) * .4)
        self.assertTrue(0 <= score <= 1)

    def test_group_mean(self) -> None:
        """Include zero-affinity users in the group mean."""
        place = score_places(self.group, [self.place])[0]
        self.assertAlmostEqual(place["group_score"], sum(place["user_scores"].values()) / 2)

    def test_actual_category_no_cycling(self) -> None:
        """Category is independent of user preference ordering and place names."""
        places = [{**self.place, "name": "카페처럼 보이는 이름", "category": "outdoor"}]
        result = generate_itinerary(self.conditions, self.profiles, places)
        self.assertEqual(result["schedule"][0]["category"], "outdoor")
        reversed_profiles = list(reversed(self.profiles))
        self.assertEqual(generate_itinerary(self.conditions, reversed_profiles, places)["schedule"][0]["category"], "outdoor")

    def test_coverage(self) -> None:
        """Coverage is each user's best score among selected candidates."""
        places = score_places(self.group, [self.place, {**self.place, "place_id": "p2", "category": "outdoor", "keywords": []}])
        selected, coverage = select_places(places, ["1", "2"])
        for user in coverage:
            self.assertEqual(coverage[user], max(place["user_scores"][user] for place in selected))

    def test_fairness_changes_selection(self) -> None:
        """A less-covered user's option beats a higher-mean redundant stop."""
        places = [
            {"place_id": "a", "group_score": .6, "user_scores": {"1": 1., "2": .2}},
            {"place_id": "b", "group_score": .575, "user_scores": {"1": .95, "2": .2}},
            {"place_id": "c", "group_score": .4, "user_scores": {"1": 0., "2": .8}},
        ]
        selected, coverage = select_places(places, ["1", "2"], 2)
        self.assertEqual([place["place_id"] for place in selected], ["a", "c"])
        self.assertEqual(coverage, {"1": 1., "2": .8})

    def test_no_duplicate_selection(self) -> None:
        """Each place ID appears at most once; duplicate candidate IDs are rejected."""
        scored = score_places(self.group, [self.place])
        selected, _ = select_places(scored, ["1", "2"])
        self.assertEqual(len(selected), 1)
        with self.assertRaises(ValueError):
            score_places(self.group, [self.place, self.place])

    def test_max_stops(self) -> None:
        """Even many candidates produce at most MAX_STOPS."""
        places = [{**self.place, "place_id": str(index)} for index in range(8)]
        self.assertEqual(len(generate_itinerary(self.conditions, self.profiles, places)["schedule"]), MAX_STOPS)

    def test_related_users(self) -> None:
        """At-mean users are included, using integer user IDs."""
        self.assertEqual(related_users({"user_scores": {"1": .6, "2": .2, "3": .4}, "group_score": .4}), [1, 3])
        self.assertEqual(related_users({"user_scores": {"1": .1, "2": .2}, "group_score": .9}), [2])

    def test_reason(self) -> None:
        """Reasons cite category and matched keywords from scored evidence."""
        place = score_places(self.group, [self.place])[0]
        reason = build_reason(place, related_users(place))
        self.assertIn("1번", reason)
        self.assertIn("cafe", reason)
        self.assertIn("dessert", reason)

    def test_time_distribution(self) -> None:
        """Four stops are evenly spaced in seven hours, before the end time."""
        places = score_places(self.group, [{**self.place, "place_id": str(i)} for i in range(4)])
        self.assertEqual([item["time"] for item in generate_schedule(places, self.conditions["time"])], ["13:00", "14:45", "16:30", "18:15"])
        with self.assertRaises(ValueError):
            generate_schedule(places, "20:00 ~ 13:00")

    def test_ai1_sample_end_to_end(self) -> None:
        """AI1 sample and candidate fixture flow into a JSON-compatible itinerary."""
        profiles = load_preference_profiles(SAMPLE_PROFILES_PATH)
        places = json.loads(SAMPLE_PLACES_PATH.read_text(encoding="utf-8"))
        before = json.dumps(profiles)
        result = generate_itinerary(self.conditions, profiles, places)
        self.assertEqual(json.dumps(profiles), before)
        self.assertEqual(len(result["schedule"]), 4)
        self.assertEqual(set(result["preference_coverage"]), {"1", "2", "3"})
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        categories = {place["place_id"]: place["category"] for place in places}
        for stop in result["schedule"]:
            self.assertEqual(stop["category"], categories[stop["place_id"]])

    def test_empty_places_and_users(self) -> None:
        """No candidates leaves zero coverage; no users produces no stops."""
        result = generate_itinerary(self.conditions, self.profiles, [])
        self.assertEqual(result["schedule"], [])
        self.assertEqual(result["preference_coverage"], {"1": 0, "2": 0})
        self.assertEqual(generate_itinerary(self.conditions, [], [self.place])["schedule"], [])

    def test_unverifiable_conditions(self) -> None:
        """Do not claim dinner or price conditions have been fulfilled."""
        result = generate_itinerary(self.conditions, self.profiles, [self.place])
        self.assertEqual(result["unverifiable_conditions"], ["저녁 식사 포함"])
        self.assertEqual(result["verifiable_conditions"], [])


if __name__ == "__main__":
    unittest.main()
