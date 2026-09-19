"""실행: python ai/preference_analyzer/youtube_sample.py "YOUTUBE_URL"."""

import argparse
import json
import sys

from pydantic import ValidationError

if __package__:
    from .content_parser import analyze_content
    from .metadata_fetcher import MetadataError, extract_youtube_video_id, fetch_youtube_metadata
    from .preference import PreferenceDB
    from .schemas import ContentInput
    from .youtube_pipeline import metadata_to_content
else:
    from content_parser import analyze_content
    from metadata_fetcher import MetadataError, extract_youtube_video_id, fetch_youtube_metadata
    from preference import PreferenceDB
    from schemas import ContentInput
    from youtube_pipeline import metadata_to_content


def main() -> int:
    """URL 하나를 분석하고 순서대로 결과를 출력한다. 예상 오류에는 종료 코드 1."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="YouTube 공개 메타데이터로 취향 분석")
    parser.add_argument("url")
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()
    try:
        ContentInput(user_id=args.user_id)
        print("Video ID:", extract_youtube_video_id(args.url), sep="\n", flush=True)
        metadata = fetch_youtube_metadata(args.url)
        print("\nYouTube Metadata:")
        print(metadata.model_dump_json(indent=2), flush=True)
        analyzed = analyze_content(metadata_to_content(args.user_id, metadata))
        print("\nAnalyzed Content:")
        print(analyzed.model_dump_json(indent=2))
        profile = PreferenceDB().update(args.user_id, [analyzed])
        print("\nPreference Profile:")
        print(json.dumps(profile.model_dump(), ensure_ascii=False, indent=2))
        return 0
    except MetadataError as exc:
        print(f"오류: {exc}")
        return 1
    except ValidationError:
        print("오류: 사용자 ID는 양의 정수여야 하며 입력 데이터는 스키마에 맞아야 합니다.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
