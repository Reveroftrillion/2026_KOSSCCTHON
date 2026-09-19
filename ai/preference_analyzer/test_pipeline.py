"""네트워크나 실제 키 없이 실행하는 회귀 및 LLM 오류 처리 테스트."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from ai.preference_analyzer import AnalyzedContent, PreferenceDB, analyze_content
from ai.preference_analyzer.sample import CONTENTS


class PipelineTests(unittest.TestCase):
    """기존 계산과 새 LLM 성공·실패 경로를 검증한다."""

    def setUp(self) -> None:
        """실제 환경변수 및 외부 요청에서 테스트를 격리한다."""
        self.env = patch.dict(os.environ, {"LLM_API_KEY": "", "LLM_MODEL": "test-model", "LLM_BASE_URL": "https://ai.cs.kookmin.ac.kr/v1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.output = io.StringIO()
        self.capture = redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)
        self.content = {"user_id": 1, "title": "성수 카페", "description": "디저트와 데이트"}
        self.payload = {
            "category": "cafe", "keywords": ["Desserts", "DATE", "dating"],
            "area": "성수", "activity": "카페 방문", "place_name": None,
            "recommended_time": None,
        }

    def mock_response(self, payload: dict | None = None, **changes: object) -> SimpleNamespace:
        """OpenAI 응답의 필요한 속성을 구성한다."""
        fields = {"finish_reason": "stop", "content": json.dumps(payload or self.payload), "refusal": None}
        fields.update(changes)
        message = SimpleNamespace(content=fields["content"], refusal=fields["refusal"])
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=fields["finish_reason"], message=message)])

    def run_llm(self, response: SimpleNamespace | Exception) -> AnalyzedContent:
        """실제 LLM 분석 로직을 모의 SDK 응답으로 실행한다."""
        with patch.dict(os.environ, {"LLM_API_KEY": "test-placeholder"}), patch("openai.OpenAI") as factory:
            request = factory.return_value.__enter__.return_value.chat.completions.create
            if isinstance(response, Exception):
                request.side_effect = response
            else:
                request.return_value = response
            result = analyze_content(self.content)
            self.assertEqual(factory.call_args.kwargs["timeout"], 15.0)
            self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
            self.assertEqual(factory.call_args.kwargs["base_url"], os.environ["LLM_BASE_URL"].strip() or "https://ai.cs.kookmin.ac.kr/v1")
            self.assertEqual(request.call_args.kwargs["model"], os.environ["LLM_MODEL"].strip() or "claude-sonnet-4-5")
            self.assertNotIn("response_format", request.call_args.kwargs)
            self.assertNotIn("user_id", json.loads(request.call_args.kwargs["messages"][1]["content"]))
            return result

    def test_original_profiles_without_key(self) -> None:
        """8개 Mock의 기존 카테고리·키워드 비율을 보존한다."""
        db = PreferenceDB()
        with patch("ai.preference_analyzer.content_parser.analyze_with_llm") as llm:
            for content in CONTENTS:
                db.update(content["user_id"], [analyze_content(content)])
            llm.assert_not_called()
        self.assertEqual(db.get_profile(1).category_preferences,
                         {"cafe": .5, "exhibition": .167, "food": .167, "shopping": .167})
        self.assertEqual(db.get_profile(1).keyword_preferences,
                         {"cafe": .5, "date": .5, "dessert": .5, "exhibition": .167,
                          "food": .167, "photo": .167, "quiet": .167, "shopping": .167})
        self.assertEqual(db.get_profile(2).category_preferences, {"exhibition": .5, "outdoor": .5})

    def test_llm_success_and_profile(self) -> None:
        """LLM 결과가 정규화되고 취향 계산으로 전달된다."""
        result = self.run_llm(self.mock_response())
        self.assertEqual(result.keywords, ["dessert", "date"])
        self.assertEqual((result.user_id, result.title, result.area), (1, "성수 카페", "성수"))
        self.assertIn("[Parser] llm", self.output.getvalue())
        self.assertEqual(PreferenceDB().update(1, [result]).keyword_preferences, {"dessert": 1., "date": 1.})

    def test_category_alias(self) -> None:
        """restaurant를 food로 정규화한다."""
        self.assertEqual(self.run_llm(self.mock_response({**self.payload, "category": " Restaurant "})).category, "food")

    def test_invalid_responses_fall_back(self) -> None:
        """잘못된 JSON·분류·키워드·누락·불완전 응답에서 규칙으로 복구한다."""
        responses = [
            self.mock_response(content="not JSON"),
            self.mock_response(content=""),
            self.mock_response(content=None),
            self.mock_response(refusal="Cannot analyze"),
            SimpleNamespace(choices=[]),
            self.mock_response(finish_reason="length"),
            self.mock_response({**self.payload, "category": "invented"}),
            self.mock_response({**self.payload, "keywords": []}),
            self.mock_response({**self.payload, "keywords": ["a very long sentence with no useful keyword"]}),
            self.mock_response({**self.payload, "keywords": "date"}),
            self.mock_response(content='{"category":"cafe"}'),
        ]
        for response in responses:
            with self.subTest(response=response):
                result = self.run_llm(response)
                self.assertEqual(result.keywords, ["dessert", "date", "cafe"])
        self.assertNotIn("[Parser] llm", self.output.getvalue())

    def test_api_failures_fall_back(self) -> None:
        """호출 오류·타임아웃에도 파이프라인이 유지된다."""
        for error in [TimeoutError("private error"), RuntimeError("private error")]:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(self.run_llm(error).category, "cafe")
        self.assertNotIn("private error", self.output.getvalue())

    def test_missing_sdk_falls_back(self) -> None:
        """SDK 설치 전에도 규칙 분석을 사용할 수 있다."""
        with patch.dict(os.environ, {"LLM_API_KEY": "test-placeholder"}), patch.dict("sys.modules", {"openai": None}):
            self.assertEqual(analyze_content(self.content).category, "cafe")

    def test_ungrounded_locations_removed(self) -> None:
        """원문에 없는 지역·장소는 null로 바꾼다."""
        result = self.run_llm(self.mock_response({**self.payload, "area": "부산", "place_name": "상상카페"}))
        self.assertIsNone(result.area)
        self.assertIsNone(result.place_name)

    def test_explicit_place_preserved(self) -> None:
        """원문에 명시된 장소는 보존한다."""
        self.content["title"] = "성수 테스트카페 방문"
        result = self.run_llm(self.mock_response({**self.payload, "place_name": "테스트카페"}))
        self.assertEqual(result.place_name, "테스트카페")

    def test_title_only_and_empty_input(self) -> None:
        """설명이 없거나 텍스트 전체가 비어 있어도 규칙 분석이 가능하다."""
        self.assertEqual(analyze_content({"user_id": 1, "title": "카페"}).category, "cafe")
        self.assertEqual(analyze_content({"user_id": 1}).category, "unknown")
        self.assertEqual(PreferenceDB().get_profile(1).category_preferences, {})

    def test_keyword_limit(self) -> None:
        """중복·대소문자를 정리하고 7개로 제한한다."""
        result = AnalyzedContent(category="food", keywords=["DATE", "date", "photo", "art", "quiet", "local", "indoor", "food", "nature"])
        self.assertEqual(len(result.keywords), 7)
        self.assertEqual(result.keywords.count("date"), 1)

    def test_json_code_fence(self) -> None:
        """Claude가 JSON 전체를 코드 블록으로 감싸도 검증한다."""
        result = self.run_llm(self.mock_response(content="```json\n" + json.dumps(self.payload) + "\n```"))
        self.assertEqual(result.keywords, ["dessert", "date"])
        self.assertIn("[Parser] llm", self.output.getvalue())

    def test_default_and_alternative_model(self) -> None:
        """빈 설정에는 국민대 기본값을 쓰고 Sonnet 4.6 설정도 전달한다."""
        for model in ("", "claude-sonnet-4-6"):
            with self.subTest(model=model), patch.dict(os.environ, {"LLM_BASE_URL": "", "LLM_MODEL": model}):
                self.assertEqual(self.run_llm(self.mock_response()).category, "cafe")

    def test_old_openai_key_does_not_enable_llm(self) -> None:
        """기존 OpenAI 환경변수만으로는 LLM을 호출하지 않는다."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-placeholder"}), patch("ai.preference_analyzer.content_parser.analyze_with_llm") as llm:
            self.assertEqual(analyze_content(self.content).category, "cafe")
            llm.assert_not_called()

    def test_sdk_http_request_and_sample(self) -> None:
        """실제 SDK의 국민대 Chat 요청과 수정 없는 sample 전체 실행을 검증한다."""
        import httpx
        from openai import OpenAI
        from ai.preference_analyzer.sample import main

        calls = []

        def handle(request: httpx.Request) -> httpx.Response:
            """네트워크 대신 요청을 검증하고 Chat 형식 응답을 제공한다."""
            self.assertEqual(str(request.url), "https://ai.cs.kookmin.ac.kr/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-placeholder")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "claude-sonnet-4-5")
            self.assertNotIn("response_format", body)
            self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
            calls.append(body)
            return httpx.Response(200, json={
                "id": "mock-chat", "object": "chat.completion", "created": 0,
                "model": body["model"], "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps(self.payload)}}],
            })

        def make_client(**kwargs: object) -> OpenAI:
            """SDK 전송 계층만 교체하고 클라이언트 구성은 실제 구현을 따른다."""
            return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle)))

        with patch.dict(os.environ, {"LLM_API_KEY": "test-placeholder", "LLM_MODEL": ""}), patch("openai.OpenAI", side_effect=make_client):
            main()
        self.assertEqual(len(calls), 8)
        self.assertEqual(self.output.getvalue().count("[Parser] llm"), 8)
        self.assertIn('"category_preferences"', self.output.getvalue())
        self.assertNotIn("fallback", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
