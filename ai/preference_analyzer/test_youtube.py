"""YouTube 수집·분석 통합 테스트. 외부 HTTP는 모두 모의 처리한다."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from ai.preference_analyzer import PreferenceDB
from ai.preference_analyzer.metadata_fetcher import MetadataError, extract_youtube_video_id, fetch_youtube_metadata
from ai.preference_analyzer.schemas import YouTubeMetadata
from ai.preference_analyzer.youtube_pipeline import analyze_youtube_url, metadata_to_content, process_youtube_url
from ai.preference_analyzer.youtube_sample import main

VIDEO_ID = "AbC123_-xyz"
URL = f"https://www.youtube.com/shorts/{VIDEO_ID}"


class YouTubeTests(unittest.TestCase):
    """URL 검증, provider 선택, 오류 처리 및 DB 갱신을 검증한다."""

    def setUp(self) -> None:
        """환경변수와 HTTP를 격리한다."""
        env = patch.dict(os.environ, {"YOUTUBE_API_KEY": "", "LLM_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        http = patch("ai.preference_analyzer.metadata_fetcher.httpx.get")
        self.get = http.start()
        self.addCleanup(http.stop)
        self.get.return_value = self.response({"title": "성수 카페", "author_name": "TripClip"})
        self.output = io.StringIO()
        capture = redirect_stdout(self.output)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)

    def response(self, data: object, status: int = 200) -> httpx.Response:
        """httpx 상태 검증이 가능한 응답을 만든다."""
        return httpx.Response(status, json=data, request=httpx.Request("GET", "https://www.youtube.com/oembed"))

    def test_shorts_ids(self) -> None:
        """www 유무 및 공유 쿼리와 무관하게 Shorts ID를 추출한다."""
        for host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            self.assertEqual(extract_youtube_video_id(f"https://{host}/shorts/{VIDEO_ID}?si=share"), VIDEO_ID)

    def test_watch_id(self) -> None:
        """watch의 v 쿼리에서 ID를 추출한다."""
        self.assertEqual(extract_youtube_video_id(f"https://www.youtube.com/watch?t=1&v={VIDEO_ID}"), VIDEO_ID)

    def test_short_link_id(self) -> None:
        """youtu.be 공유 주소에서 ID를 추출한다."""
        self.assertEqual(extract_youtube_video_id(f"https://youtu.be/{VIDEO_ID}?t=1"), VIDEO_ID)

    def test_invalid_urls(self) -> None:
        """위장 호스트, 잘못된 ID와 경로를 네트워크 호출 전에 거부한다."""
        for url in ("invalid", "https://example.com/", f"https://youtube.com.evil.test/shorts/{VIDEO_ID}",
                    f"https://youtube.com@evil.test/shorts/{VIDEO_ID}", "https://youtube.com/watch",
                    "https://youtube.com/shorts/short", f"https://youtu.be/{VIDEO_ID}/extra",
                    f"https://youtube.com/watch?v={VIDEO_ID}&v={VIDEO_ID}", "https://[invalid"):
            with self.subTest(url=url), self.assertRaises(MetadataError):
                fetch_youtube_metadata(url)
        self.get.assert_not_called()

    def test_data_api(self) -> None:
        """키가 있으면 snippet과 썸네일을 Data API에서 추출한다."""
        self.get.return_value = self.response({"items": [{"snippet": {
            "title": "성수 카페", "description": "데이트", "tags": ["디저트"],
            "channelTitle": "TripClip", "thumbnails": {"high": {"url": "https://example.com/high.jpg"}},
        }}]})
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-placeholder"}):
            metadata = fetch_youtube_metadata(URL)
        self.assertEqual(self.get.call_args.args[0], "https://www.googleapis.com/youtube/v3/videos")
        self.assertEqual(self.get.call_args.kwargs["params"], {"part": "snippet", "id": VIDEO_ID, "key": "test-placeholder"})
        self.assertEqual(metadata.tags, ["디저트"])
        self.assertEqual(metadata.description, "데이트")
        self.assertEqual(metadata.thumbnail_url, "https://example.com/high.jpg")

    def test_oembed(self) -> None:
        """키 없이 oEmbed를 사용하며 미제공 설명과 태그는 빈 값이다."""
        metadata = fetch_youtube_metadata(URL)
        self.assertEqual(self.get.call_args.args[0], "https://www.youtube.com/oembed")
        self.assertEqual(self.get.call_args.kwargs["params"]["url"], f"https://www.youtube.com/watch?v={VIDEO_ID}")
        self.assertEqual(self.get.call_args.kwargs["timeout"], 10.0)
        self.assertEqual((metadata.description, metadata.tags), ("", []))

    def test_metadata_conversion(self) -> None:
        """원본 정보와 사용자 ID를 기존 모델에 전달한다."""
        metadata = YouTubeMetadata(url=URL, video_id=VIDEO_ID, title="영상", tags=["성수", "카페"])
        content = metadata_to_content(7, metadata)
        self.assertEqual((content.user_id, content.title, content.tags), (7, "영상", ["성수", "카페"]))

    def test_llm_connection(self) -> None:
        """메타데이터 태그가 실제 LLM 요청 생성과 검증 경로에 전달된다."""
        self.get.return_value = self.response({"items": [{"snippet": {"title": "오늘의 장소", "tags": ["성수", "카페"]}}]})
        payload = {"category": "cafe", "keywords": ["cafe"], "area": "성수", "activity": "카페 방문", "place_name": None, "recommended_time": None}
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-placeholder", "LLM_API_KEY": "test-placeholder"}), patch("openai.OpenAI") as client:
            create = client.return_value.__enter__.return_value.chat.completions.create
            create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(payload), refusal=None))])
            result = analyze_youtube_url(1, URL)
            self.assertEqual(json.loads(create.call_args.kwargs["messages"][1]["content"])["tags"], ["성수", "카페"])
        self.assertEqual(result["analysis"]["area"], "성수")
        self.assertIn("[Parser] llm", self.output.getvalue())

    def test_claude_failure(self) -> None:
        """Claude 오류에도 규칙으로 분석하고 DB를 갱신한다."""
        db = PreferenceDB()
        with patch.dict(os.environ, {"LLM_API_KEY": "test-placeholder"}), patch("ai.preference_analyzer.content_parser.analyze_with_llm", side_effect=TimeoutError):
            result = process_youtube_url(1, URL, db)
        self.assertEqual(result["preference_profile"]["category_preferences"], {"cafe": 1.0})
        self.assertIn("[Parser] rule-based", self.output.getvalue())

    def test_network_errors(self) -> None:
        """네트워크 실패를 안전한 오류로 바꾸고 DB는 변경하지 않는다."""
        for error in (httpx.ConnectError("private details"), httpx.ReadTimeout("private details")):
            self.get.side_effect = error
            db = PreferenceDB()
            with self.assertRaises(MetadataError) as caught:
                process_youtube_url(1, URL, db)
            self.assertNotIn("private details", str(caught.exception))
            self.assertEqual(db.get_all_profiles(), {})

    def test_unavailable_and_malformed(self) -> None:
        """공개 불가, 제목 누락, 잘못된 응답을 오류로 처리한다."""
        for response in (self.response({}, 404), self.response({"title": " "}), self.response([]),
                         httpx.Response(200, text="not JSON", request=httpx.Request("GET", "https://www.youtube.com/oembed"))):
            self.get.return_value = response
            with self.assertRaises(MetadataError):
                fetch_youtube_metadata(URL)
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-placeholder"}):
            self.get.return_value = self.response({"items": []})
            with self.assertRaises(MetadataError):
                fetch_youtube_metadata(URL)
            self.get.return_value = self.response({}, 403)
            with self.assertRaises(MetadataError):
                fetch_youtube_metadata(URL)

    def test_tags_rule_fallback_and_accumulation(self) -> None:
        """태그만으로도 규칙 분석이 가능하며 같은 DB에 누적된다."""
        self.get.return_value = self.response({"items": [{"snippet": {"title": "오늘", "tags": ["카페"]}}]})
        db = PreferenceDB()
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-placeholder"}):
            process_youtube_url(1, URL, db)
        self.get.return_value = self.response({"title": "전시"})
        process_youtube_url(1, URL, db)
        self.assertEqual(db.get_profile(1).category_preferences, {"cafe": .5, "exhibition": .5})

    def test_cli_output_order_and_error(self) -> None:
        """CLI 출력 순서와 오류 시 종료 코드를 검증한다."""
        with patch("sys.argv", ["youtube_sample.py", URL]):
            self.assertEqual(main(), 0)
        output = self.output.getvalue()
        labels = ["Video ID:", "YouTube Metadata:", "[Parser]", "Analyzed Content:", "Preference Profile:"]
        self.assertEqual(sorted(output.index(label) for label in labels), [output.index(label) for label in labels])
        with patch("sys.argv", ["youtube_sample.py", "bad-url"]):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
