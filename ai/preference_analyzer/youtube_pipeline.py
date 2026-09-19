"""YouTube 메타데이터를 기존 콘텐츠 분석 및 메모리 취향 DB에 연결한다."""

from typing import Any

if __package__:
    from .content_parser import analyze_content
    from .metadata_fetcher import fetch_youtube_metadata
    from .preference import PreferenceDB
    from .schemas import AnalyzedContent, ContentInput, YouTubeMetadata
else:
    from content_parser import analyze_content
    from metadata_fetcher import fetch_youtube_metadata
    from preference import PreferenceDB
    from schemas import AnalyzedContent, ContentInput, YouTubeMetadata


def metadata_to_content(user_id: int, metadata: YouTubeMetadata) -> ContentInput:
    """수집한 제목·설명·태그를 손실 없이 기존 입력 모델로 변환한다."""
    return ContentInput(user_id=user_id, url=metadata.url, title=metadata.title,
                        description=metadata.description, tags=metadata.tags)


def analyze_youtube_url(user_id: int, url: str) -> dict[str, Any]:
    """URL을 수집·분석한다. 수집 실패 시 MetadataError를 호출자에게 전달한다."""
    ContentInput(user_id=user_id)  # 네트워크 호출 전에 사용자 입력을 검증한다.
    metadata = fetch_youtube_metadata(url)
    analysis = analyze_content(metadata_to_content(user_id, metadata))
    return {"metadata": metadata.model_dump(mode="json"), "analysis": analysis.model_dump(mode="json")}


def process_youtube_url(user_id: int, url: str, preference_db: PreferenceDB) -> dict[str, Any]:
    """수집·분석 성공 시에만 취향을 누적하고 메타데이터·분석·프로필을 반환한다."""
    result = analyze_youtube_url(user_id, url)
    analysis = AnalyzedContent.model_validate(result["analysis"])
    result["preference_profile"] = preference_db.update(user_id, [analysis]).model_dump()
    return result
