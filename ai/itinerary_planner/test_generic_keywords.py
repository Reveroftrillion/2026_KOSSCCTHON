"""Regression checks for generic-only affinity across unsupported categories."""

import unittest

from ai.itinerary_planner.place_scoring import score_user_place


class GenericKeywordTests(unittest.TestCase):
    """Keep the scoring formula while bounding weak cross-category evidence."""

    def test_food_to_shopping_generic_only(self) -> None:
        """The reported 0.4 score is bounded to 0.2 for each generic keyword."""
        for keyword in ("local", "date", "photo"):
            with self.subTest(keyword=keyword):
                user = {"category_preferences": {"food": 1.0}, "keyword_preferences": {keyword: 1.0}}
                result = score_user_place(user, {"category": "shopping", "keywords": [keyword]})
                self.assertEqual(result["category_score"], 0)
                self.assertEqual(result["keyword_score"], .5)
                self.assertEqual(result["user_place_score"], .2)

    def test_matching_category_unchanged(self) -> None:
        """Generic evidence remains full strength for a supported category."""
        user = {"category_preferences": {"food": 1.0}, "keyword_preferences": {"local": 1.0}}
        self.assertEqual(score_user_place(user, {"category": "food", "keywords": ["local"]})["user_place_score"], 1.0)

    def test_specific_keyword_unchanged(self) -> None:
        """Specific cross-category evidence is not limited by the generic-only cap."""
        user = {"category_preferences": {"food": 1.0}, "keyword_preferences": {"art": 1.0, "photo": 1.0}}
        self.assertEqual(score_user_place(user, {"category": "exhibition", "keywords": ["art", "photo"]})["user_place_score"], .4)

    def test_moderate_match_unchanged(self) -> None:
        """Existing 0.5 or lower generic affinity is preserved."""
        user = {"category_preferences": {}, "keyword_preferences": {"photo": .5}}
        self.assertEqual(score_user_place(user, {"category": "outdoor", "keywords": ["photo"]})["user_place_score"], .2)

    def test_zero_specific_does_not_bypass_cap(self) -> None:
        """A zero-valued specific match does not count as supporting evidence."""
        user = {"category_preferences": {}, "keyword_preferences": {"local": 1., "photo": 1., "art": 0.}}
        result = score_user_place(user, {"category": "shopping", "keywords": ["local", "photo", "art"]})
        self.assertEqual(result["user_place_score"], .2)


if __name__ == "__main__":
    unittest.main()
