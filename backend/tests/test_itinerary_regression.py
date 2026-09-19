"""Deterministic API/SQL regression tests; real AI2, fixture candidates, SQLite."""
import json
from unittest.mock import patch
from sqlalchemy import text
from backend.tests.test_backend import BackendFixture


class ItineraryRegressionTests(BackendFixture):
    def setUp(self) -> None:
        super().setUp()
        self.users = [f"00000000-0000-4000-8000-{index:012d}" for index in range(1, 4)]
        self.categories = ["food", "sightseeing", "exhibition"]
        with self.engine.begin() as db:
            for user, category in zip(self.users, self.categories):
                db.execute(text("INSERT INTO users (user_id,name,email,password_hash) VALUES (:id,:id,:email,'unused')"),
                           {"id": user, "email": user + "@example.com"})
                db.execute(text("INSERT INTO user_preferences (preference_id,user_id,category_scores,tag_scores) VALUES (:id,:id,:scores,'{}')"),
                           {"id": user, "scores": json.dumps({category: 1.0})})
        self.body.update(owner_user_id=self.users[0], end_date="2026-09-21")
        self.trip = self.create_trip()
        self.base = f"/api/trips/{self.trip}"
        for user in self.users[1:]:
            self.assertEqual(self.client.post(self.base + "/members", json={"user_id": user}).status_code, 201)
        provider = patch("backend.services.itinerary_service.search_places", return_value=self.candidates("initial"))
        self.provider = provider.start()
        self.addCleanup(provider.stop)

    def candidates(self, version: str) -> list[dict]:
        """Two equal-quality candidates per category; IDs provide deterministic tie breaks."""
        return [{"place_id": f"{version}-{category}-{index}", "name": f"{version} {category} {index}",
                 "category": category, "keywords": [], "lat": 37.54 + index / 1000,
                 "lng": 127.05, "address": "fixture address", "source": "kakao"}
                for category in self.categories for index in range(2)]

    def generate(self, date: str = "2026-09-20") -> dict:
        response = self.client.post(self.base + "/itinerary", json={"date": date, "user_conditions": []})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def assert_current_stops(self, result: dict) -> None:
        """Assert current day has one parent and precisely the returned child set."""
        with self.engine.connect() as db:
            parents = db.execute(text("SELECT itinerary_id FROM trip_itineraries WHERE trip_id=:trip AND day_number=:day"),
                                 {"trip": self.trip, "day": result["day_number"]}).scalars().all()
            self.assertEqual(len(parents), 1)
            stops = db.execute(text("SELECT place_id FROM itinerary_places WHERE itinerary_id=:id"),
                               {"id": parents[0]}).scalars().all()
        self.assertEqual(len(stops), len(result["schedule"]))
        self.assertEqual(set(stops), {stop["place_id"] for stop in result["schedule"]})

    def test_fairness_covers_three_disjoint_preferences(self) -> None:
        result = self.generate()
        self.assertGreaterEqual({stop["category"] for stop in result["schedule"]}, set(self.categories))
        covered = {user for stop in result["schedule"] for user in stop["related_users"]}
        self.assertGreaterEqual(covered, set(self.users))
        for user, category in zip(self.users, self.categories):
            reflection = result["preference_reflection"][user]
            self.assertEqual(reflection["preference_reflection_percent"], 100)
            self.assertIn(category, reflection["matched_categories"])
        # Reversing candidates must not change selected membership; no route order assertion.
        self.provider.return_value = list(reversed(self.candidates("initial")))
        again = self.generate()
        self.assertEqual({s["place_id"] for s in result["schedule"]}, {s["place_id"] for s in again["schedule"]})

    def test_same_day_keeps_only_new_stop_set(self) -> None:
        old = self.generate()
        self.provider.return_value = self.candidates("replacement")
        current = self.generate()
        self.assertEqual(len(current["schedule"]), 4)
        self.assertTrue({s["place_id"] for s in old["schedule"]}.isdisjoint({s["place_id"] for s in current["schedule"]}))
        self.assert_current_stops(current)
        self.assertEqual(self.client.get(self.base + "/itineraries").json(), [current])

    def test_two_days_replace_independently(self) -> None:
        current = {1: self.generate(), 2: self.generate("2026-09-21")}
        self.assertEqual([current[day]["day_number"] for day in (1, 2)], [1, 2])
        for day, date in ((1, "2026-09-20"), (2, "2026-09-21")):
            self.provider.return_value = self.candidates(f"day-{day}-replacement")
            current[day] = self.generate(date)
            self.assertEqual(self.client.get(self.base + "/itineraries").json(), [current[1], current[2]])
            for expected in current.values():
                self.assertEqual(self.client.get(self.base + "/itineraries/" + expected["itinerary_id"]).json(), expected)
                self.assert_current_stops(expected)

    def test_member_without_preferences_has_null_reflection_and_finite_json(self) -> None:
        empty_user = self.users[1]
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM user_preferences WHERE user_id=:id"), {"id": empty_user})
        profiles = self.client.get(self.base + "/preferences").json()
        self.assertIn({"user_id": empty_user, "category_preferences": {}, "keyword_preferences": {}}, profiles)
        result = self.generate()
        self.assertTrue(result["schedule"])
        self.assertEqual(result["preference_reflection"][empty_user], {
            "matched_categories": [], "total_categories": 0, "preference_reflection_percent": None})
        self.assertEqual(result["preference_coverage"][empty_user], 0)
        for stop in result["schedule"]:
            self.assertEqual(stop["user_scores"][empty_user], 0)
            self.assertNotIn(empty_user, stop["related_users"])
        for user in (self.users[0], self.users[2]):
            self.assertEqual(result["preference_reflection"][user]["preference_reflection_percent"], 100)
        json.dumps(result, allow_nan=False)
        with self.engine.connect() as db:
            for table, fields in (("trip_itineraries", "result_json,preference_coverage,preference_reflection"),
                                  ("itinerary_places", "related_users,user_scores")):
                for record in db.execute(text(f"SELECT {fields} FROM {table}")):
                    for value in record:
                        json.dumps(json.loads(value), allow_nan=False)
        self.assertEqual(self.client.get(self.base + "/itineraries").json(), [result])
