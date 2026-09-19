"""AI1 score-preserving integration and legacy AI2 regression tests."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from ai.itinerary_planner.group_preference import (
    analyze_preferences, balance_group_preferences, build_group_preferences, load_preference_profiles,
)
from ai.preference_analyzer import AnalyzedContent, PreferenceDB, export_all_preference_profiles

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "ai/preference_analyzer/sample_group_preferences.json"


class GroupPreferenceTests(unittest.TestCase):
    """Check scores, averaging, direct exports and backward compatibility."""

    def setUp(self) -> None:
        """Prepare three users, including one with no recorded preferences."""
        self.profiles = [
            {"user_id": 1, "category_preferences": {"cafe": .5}, "keyword_preferences": {"photo": .6}},
            {"user_id": 2, "category_preferences": {"cafe": .2, "food": .8}, "keyword_preferences": {"photo": .3, "date": .9}},
            {"user_id": 3, "category_preferences": {}, "keyword_preferences": {}},
        ]

    def test_ai1_sample_loading(self) -> None:
        """Load the real AI1 shared fixture without transforming scores."""
        profiles = load_preference_profiles(SAMPLE)
        result = build_group_preferences(profiles)
        self.assertEqual(len(result["users"]), 3)
        self.assertEqual(result["group_category_preferences"]["cafe"], .25)
        self.assertEqual(result["group_keyword_preferences"]["photo"], .417)
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)

    def test_category_scores_preserved(self) -> None:
        """User scores retain their exact values, not just preference names."""
        result = build_group_preferences(self.profiles)
        for profile in self.profiles:
            self.assertEqual(result["users"][str(profile["user_id"])]["category_preferences"], profile["category_preferences"])

    def test_keyword_scores_preserved(self) -> None:
        """Keyword scores are independent of category scores."""
        result = build_group_preferences(self.profiles)
        for profile in self.profiles:
            self.assertEqual(result["users"][str(profile["user_id"])]["keyword_preferences"], profile["keyword_preferences"])

    def test_category_average(self) -> None:
        """Average over every user, rounding to three decimals."""
        self.assertEqual(build_group_preferences(self.profiles)["group_category_preferences"], {"cafe": .233, "food": .267})

    def test_keyword_average(self) -> None:
        """Use the same all-user denominator for keywords."""
        self.assertEqual(build_group_preferences(self.profiles)["group_keyword_preferences"], {"photo": .3, "date": .3})

    def test_missing_preferences_are_zero(self) -> None:
        """An empty user still contributes to the group denominator."""
        self.assertEqual(build_group_preferences(self.profiles[:2])["group_category_preferences"]["cafe"], .35)
        self.assertEqual(build_group_preferences(self.profiles)["group_category_preferences"]["cafe"], .233)

    def test_direct_export(self) -> None:
        """Consume AI1 exports directly, also allowing optional evidence."""
        db = PreferenceDB()
        db.update(1, [AnalyzedContent(category="cafe", keywords=["dessert"])])
        db.update(2, [AnalyzedContent(category="food", keywords=["local"])])
        for evidence in (False, True):
            result = build_group_preferences(export_all_preference_profiles(db, include_evidence=evidence))
            self.assertEqual(result["group_category_preferences"], {"cafe": .5, "food": .5})
            self.assertEqual(result["group_keyword_preferences"], {"dessert": .5, "local": .5})

    def test_analysis_and_balance_preserve_scores(self) -> None:
        """Existing AI2 entry functions also carry the scored contract."""
        analysis = analyze_preferences(self.profiles)
        balanced = balance_group_preferences(analysis, {"1": ["카페"]})
        for key, value in build_group_preferences(self.profiles).items():
            self.assertEqual(analysis[key], value)
            self.assertEqual(balanced[key], value)
        self.assertEqual(balanced["group_preference_profile"]["1"]["saved_places"], ["카페"])

    def test_legacy_sample(self) -> None:
        """Legacy category lists, saved places and CLI scripts still work."""
        sample = json.loads((Path(__file__).with_name("sample_input.json")).read_text(encoding="utf-8"))
        analysis = analyze_preferences(sample["personal_preference_db"])
        self.assertEqual(analysis["common_preferences"], ["Activity", "Cafe", "Exhibition", "Shopping"])
        self.assertEqual(analysis["individual_only_preferences"], {"원영": ["Food"], "민수": ["Popup"], "지수": ["Photo"]})
        balanced = balance_group_preferences(analysis, sample["group_saved_places"])
        self.assertEqual(balanced["group_preference_profile"]["원영"]["saved_places"], sample["group_saved_places"]["원영"])
        for script in ("group_preference.py", "itinerary_generator.py"):
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name(script))], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_and_validation(self) -> None:
        """Empty input is valid; duplicates and invalid scores are rejected."""
        self.assertEqual(build_group_preferences([]), {"users": {}, "group_category_preferences": {}, "group_keyword_preferences": {}})
        with self.assertRaises(ValueError):
            build_group_preferences([self.profiles[0], self.profiles[0]])
        for score in (float("nan"), float("inf"), -1, 1.1, True, "0.5"):
            with self.subTest(score=score), self.assertRaises(ValueError):
                build_group_preferences([{"user_id": 1, "category_preferences": {"cafe": score}, "keyword_preferences": {}}])

    def test_no_input_mutation(self) -> None:
        """Returned user score maps do not alias the input."""
        result = build_group_preferences(self.profiles)
        result["users"]["1"]["category_preferences"]["cafe"] = 0
        self.assertEqual(self.profiles[0]["category_preferences"]["cafe"], .5)


if __name__ == "__main__":
    unittest.main()
