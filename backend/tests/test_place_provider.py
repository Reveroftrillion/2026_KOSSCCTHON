"""Kakao tests with an HTTP mock; never contact external services."""
import os
import unittest
from unittest.mock import patch
import httpx
from backend.services import place_service as service
from backend.services.common import ServiceError


def document(identifier: str = "1") -> dict:
    """Build a representative Kakao response document."""
    return {"id": identifier, "place_name": "성수 카페", "x": "127.056", "y": "37.544",
            "category_name": "음식점 > 카페", "category_group_code": "CE7"}


class PlaceProviderTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"KAKAO_REST_API_KEY": "test-placeholder"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.factory = patch.object(service.httpx, "Client")
        self.client = self.factory.start().return_value.__enter__.return_value
        self.addCleanup(self.factory.stop)

    def response(self, body=None, status=200):
        return httpx.Response(status, json=body, request=httpx.Request("GET", service.KAKAO_URL))

    def test_category_mapping(self):
        pairs = {"음식점 > 카페": "cafe", "음식점 > 술집 > 호프": "nightlife", "여행 > 공원": "outdoor",
                 "문화시설 > 미술관": "exhibition", "쇼핑": "shopping", "식당": "food", "숙박": "accommodation",
                 "관광명소": "sightseeing", "스포츠": "activity", "알수없음": "other"}
        for raw, expected in pairs.items():
            with self.subTest(raw=raw):
                self.assertEqual(service.kakao_category(raw), expected)
        self.assertEqual(service.kakao_category("", "CE7"), "cafe")

    def test_normalization(self):
        self.client.get.return_value = self.response({"documents": [document()]})
        result = service.search_places("성수", [])
        self.assertEqual(result[0], {"place_id": "1", "name": "성수 카페", "category": "cafe",
                                   "keywords": ["cafe", "음식점", "카페"], "lat": 37.544, "lng": 127.056, "source": "kakao"})
        self.assertNotIn("date", result[0]["keywords"])

    def test_queries_preserve_score_ranking(self):
        profiles = [{"category_preferences": {"food": .9, "cafe": .1}}, {"category_preferences": {"cafe": .2}}]
        self.assertEqual(service.search_queries("성수", profiles), ["성수 맛집", "성수 카페"])
        self.assertEqual(service.search_queries("성수", []), ["성수 관광명소"])

    def test_deduplication(self):
        self.client.get.return_value = self.response({"documents": [document(), document()]})
        profiles = [{"category_preferences": {"food": .5, "cafe": .5}}]
        self.assertEqual(len(service.search_places("성수", profiles)), 1)
        self.assertEqual(self.client.get.call_count, 2)

    def test_request_and_candidate_limits(self):
        self.client.get.side_effect = [self.response({"documents": [document(f"{i}-{j}") for j in range(10)]}) for i in range(4)]
        profiles = [{"category_preferences": {category: 1 for category in service.CATEGORIES}}]
        self.assertEqual(len(service.search_places("성수", profiles)), 20)
        self.assertEqual(self.client.get.call_count, 4)
        for call in self.client.get.call_args_list:
            self.assertEqual(call.kwargs["params"]["size"], 5)
            self.assertEqual(call.kwargs["params"]["page"], 1)

    def test_missing_key_mock(self):
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}):
            self.assertTrue(all(p["source"] == "mock" for p in service.search_places("성수", [])))
        self.client.get.assert_not_called()

    def test_http_errors(self):
        for status, expected in [(401, 502), (429, 503), (500, 502), (503, 503)]:
            with self.subTest(status=status):
                self.client.get.return_value = self.response({"secret": "test-placeholder"}, status)
                with self.assertRaises(ServiceError) as error:
                    service.search_places("성수", [])
                self.assertEqual(error.exception.status, expected)
                self.assertNotIn("test-placeholder", str(error.exception))

    def test_timeout(self):
        self.client.get.side_effect = httpx.ReadTimeout("private")
        with self.assertRaises(ServiceError) as error:
            service.search_places("성수", [])
        self.assertEqual(error.exception.status, 502)

    def test_invalid_json_and_contract(self):
        for response in [httpx.Response(200, text="invalid", request=httpx.Request("GET", service.KAKAO_URL)),
                         self.response({"documents": {}}), self.response({"documents": [{**document(), "x": "nan"}]}),
                         self.response({"documents": [{}]})]:
            with self.subTest(response=response):
                self.client.get.return_value = response
                with self.assertRaises(ServiceError):
                    service.search_places("성수", [])

    def test_empty_results_explicit_error(self):
        self.client.get.return_value = self.response({"documents": []})
        with self.assertRaises(ServiceError) as error:
            service.search_places("성수", [])
        self.assertEqual(error.exception.status, 503)
