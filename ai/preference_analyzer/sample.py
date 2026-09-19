"""실행: python ai/preference_analyzer/sample.py (Python 3.10 이상)."""

import json
import sys

if __package__:
    from .content_parser import analyze_content
    from .preference import PreferenceDB
    from .schemas import ContentInput
else:
    from content_parser import analyze_content
    from preference import PreferenceDB
    from schemas import ContentInput


CONTENTS = [
    {"user_id": 1, "url": "https://example.com/shortform/1", "title": "성수에서 꼭 가야 하는 감성 카페", "description": "디저트가 맛있고 데이트하기 좋은 곳"},
    {"user_id": 1, "title": "성수 디저트 카페 추천", "description": "데이트 코스로 추천"},
    {"user_id": 1, "title": "서울에서 요즘 제일 핫한 전시회", "description": "사진 찍기 좋은 전시"},
    {"user_id": 1, "title": "홍대 맛집 추천", "description": "연인과 가기 좋은 식당"},
    {"user_id": 1, "title": "연남의 조용한 카페", "description": "커피와 케이크를 즐기는 시간"},
    {"user_id": 1, "title": "강남 쇼핑 코스", "description": "백화점과 편집숍 방문"},
    {"user_id": 2, "title": "서울 공원 산책", "description": "자연 속에서 사진 찍기"},
    {"user_id": 2, "title": "부산 미술관 전시", "description": "조용한 전시 관람"},
]


def main() -> None:
    """Mock 콘텐츠를 순차 분석·누적하여 사용자별 최종 취향을 출력한다."""
    # Windows에서도 콘솔 및 리다이렉션 출력에 한글을 유지한다.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db = PreferenceDB()
    analyzed = []
    for raw_content in CONTENTS:
        content = ContentInput.model_validate(raw_content)
        result = analyze_content(content)
        analyzed.append({"user_id": content.user_id, "title": content.title, **result.model_dump()})
        db.update(content.user_id, [result])

    print("Analyzed Contents:")
    print(json.dumps(analyzed, ensure_ascii=False, indent=2))
    print("\nPreference Profile (in-memory DB):")
    print(json.dumps(
        {user_id: profile.model_dump() for user_id, profile in db.get_all_profiles().items()},
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
