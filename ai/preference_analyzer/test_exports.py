"""팀 간 전달용 JSON 계약과 선택적 콘텐츠 근거를 검증한다."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from ai.preference_analyzer import (
    AnalyzedContent, PreferenceDB, analyze_content, export_all_preference_profiles,
    export_preference_profile, process_youtube_url,
)
from ai.preference_analyzer.schemas import PreferenceProfile, YouTubeMetadata


class ExportTests(unittest.TestCase):
    """JSON 직렬화, 조회 격리, 근거 및 URL 처리 후 export를 확인한다."""

    def setUp(self) -> None:
        """서로 다른 두 사용자의 분석 이력을 준비한다."""
        self.db = PreferenceDB()
        self.db.update(2, [AnalyzedContent(category="food", keywords=["local"])])
        self.db.update(1, [
            AnalyzedContent(category="cafe", keywords=["dessert", "dessert"], title="카페", url="https://example.com/1"),
            AnalyzedContent(category="exhibition", keywords=["photo"], title="전시"),
        ])

    def test_single_contract(self) -> None:
        """기본 export는 세 필드의 JSON 호환 dict다."""
        result = export_preference_profile(1, self.db)
        self.assertEqual(result, {"user_id": 1, "category_preferences": {"cafe": .5, "exhibition": .5},
                                  "keyword_preferences": {"dessert": .5, "photo": .5}})
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_all_sorted(self) -> None:
        """전체 사용자 배열은 ID 오름차순이며 서로의 취향을 섞지 않는다."""
        results = export_all_preference_profiles(self.db)
        self.assertEqual([item["user_id"] for item in results], [1, 2])
        self.assertEqual(results[1]["category_preferences"], {"food": 1.0})

    def test_empty_and_unknown(self) -> None:
        """빈 DB와 미등록 사용자 조회는 DB를 변경하지 않는다."""
        db = PreferenceDB()
        self.assertEqual(export_all_preference_profiles(db), [])
        self.assertEqual(export_preference_profile(9, db), {
            "user_id": 9, "category_preferences": {}, "keyword_preferences": {},
        })
        self.assertEqual(export_preference_profile(9, db, include_evidence=True)["evidence"], {"categories": [], "keywords": []})
        self.assertEqual(export_all_preference_profiles(db), [])

    def test_evidence(self) -> None:
        """근거와 점수가 일치하며 콘텐츠 내 중복 키워드는 한 번만 센다."""
        result = export_preference_profile(1, self.db, include_evidence=True)
        evidence = result["evidence"]["keywords"]
        self.assertEqual(evidence[0], {"keyword": "dessert", "score": .5,
                                      "sources": [{"title": "카페", "url": "https://example.com/1"}]})
        self.assertIsNone(evidence[1]["sources"][0]["url"])
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertIn("evidence", export_all_preference_profiles(self.db, include_evidence=True)[0])

    def test_export_is_detached(self) -> None:
        """반환값이나 이력 복사본을 변경해도 저장된 이력과 점수는 유지된다."""
        result = export_preference_profile(1, self.db, include_evidence=True)
        result["category_preferences"]["cafe"] = 0
        result["evidence"]["keywords"][0]["sources"][0]["title"] = "수정"
        self.db.get_contents(1)[0].keywords.clear()
        fresh = export_preference_profile(1, self.db, include_evidence=True)
        self.assertEqual(fresh["category_preferences"]["cafe"], .5)
        self.assertEqual(fresh["evidence"]["keywords"][0]["sources"][0]["title"], "카페")

    def test_invalid_user(self) -> None:
        """잘못된 사용자 ID는 기존 스키마와 동일하게 거부한다."""
        with self.assertRaises(ValidationError):
            export_preference_profile(0, self.db)

    def test_source_on_both_parser_paths(self) -> None:
        """LLM과 규칙 분석 모두 원본 제목·URL을 보존한다."""
        content = {"user_id": 1, "title": "카페", "url": "https://example.com/source"}
        for key in ("", "test-placeholder"):
            with patch.dict(os.environ, {"LLM_API_KEY": key}), redirect_stdout(io.StringIO()), patch(
                "ai.preference_analyzer.content_parser.analyze_with_llm",
                return_value=AnalyzedContent(category="cafe", title="모델이 만든 제목"),
            ):
                result = analyze_content(content)
            self.assertEqual(result.title, "카페")
            self.assertEqual(str(result.url), content["url"])

    def test_url_to_export(self) -> None:
        """Backend가 URL 처리 후 동일 DB를 export할 수 있다."""
        metadata = YouTubeMetadata(url="https://youtu.be/AbC123_-xyz", video_id="AbC123_-xyz", title="성수 디저트 카페")
        db = PreferenceDB()
        with patch.dict(os.environ, {"LLM_API_KEY": ""}), redirect_stdout(io.StringIO()), patch(
            "ai.preference_analyzer.youtube_pipeline.fetch_youtube_metadata", return_value=metadata,
        ):
            result = process_youtube_url(1, metadata.url, db)
        self.assertEqual(json.loads(json.dumps(result)), result)
        exported = export_preference_profile(1, db, include_evidence=True)
        self.assertEqual(exported["category_preferences"], {"cafe": 1.0})
        self.assertEqual(exported["evidence"]["keywords"][1]["sources"][0]["url"], metadata.url)

    def test_sample_group_json(self) -> None:
        """AI 2용 샘플은 서로 다른 3명의 유효한 기본 프로필이다."""
        path = Path(__file__).with_name("sample_group_preferences.json")
        profiles = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([item["user_id"] for item in profiles], [1, 2, 3])
        for item in profiles:
            self.assertEqual(PreferenceProfile.model_validate(item).model_dump(), item)
            self.assertAlmostEqual(sum(item["category_preferences"].values()), 1)
        self.assertEqual(len({json.dumps(item["category_preferences"], sort_keys=True) for item in profiles}), 3)


if __name__ == "__main__":
    unittest.main()
