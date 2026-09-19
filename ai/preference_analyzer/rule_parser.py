"""외부 API 없이 제목과 설명에서 콘텐츠 정보를 추출한다."""

import re
from typing import Any, Mapping

if __package__:
    from .schemas import AnalyzedContent, Category, ContentInput
else:
    from schemas import AnalyzedContent, Category, ContentInput


CATEGORY_RULES: dict[Category, tuple[str, ...]] = {
    "cafe": ("카페", "커피", "디저트", "cafe", "coffee", "dessert"),
    "exhibition": ("전시", "미술관", "박물관", "exhibition", "museum", "gallery"),
    "food": ("맛집", "식당", "음식", "레스토랑", "restaurant", "food"),
    "shopping": ("쇼핑", "편집숍", "편집샵", "백화점", "shopping", "shop"),
    "outdoor": ("산책", "공원", "등산", "하이킹", "park", "hiking"),
}
KEYWORD_RULES = {
    "dessert": ("디저트", "케이크", "dessert", "cake"),
    "date": ("데이트", "연인", "date"),
    "photo": ("사진", "포토", "photo"),
    "quiet": ("조용", "차분", "quiet"),
    "nature": ("자연", "숲", "nature"),
}
ACTIVITIES = {
    "cafe": "카페 방문", "exhibition": "전시 관람", "food": "맛집 방문",
    "shopping": "쇼핑", "outdoor": "야외 활동",
}
# 구체적인 동네를 도시명보다 우선하며, 같은 우선순위에서는 첫 언급을 선택한다.
NEIGHBORHOODS = ("성수", "홍대", "연남", "강남", "한남", "이태원", "잠실", "해운대")
CITIES = ("서울", "부산", "제주", "인천", "대구", "대전", "광주")


def _matches(text: str, term: str) -> bool:
    """한국어는 부분 문자열로, 영어는 단어 경계로 비교한다."""
    if term.isascii():
        return re.search(r"\b" + re.escape(term) + r"\b", text) is not None
    return term in text


def analyze_with_rules(content: ContentInput | Mapping[str, Any]) -> AnalyzedContent:
    """입력을 검증하고 분석한다. LLM 교체 시 이 입출력 계약을 유지한다.

    제목 일치에 2점, 설명 일치에 1점을 준다. 동점은 규칙 순서를 따른다.
    지역은 알려진 목록에서만 찾으며, 미분류 콘텐츠는 unknown으로 반환한다.
    """
    item = ContentInput.model_validate(content)
    title, description = item.title.lower(), item.description.lower()
    text = f"{title} {description}"
    scores = {
        category: sum(2 * _matches(title, term) + _matches(description, term) for term in terms)
        for category, terms in CATEGORY_RULES.items()
    }
    category = max(scores, key=scores.get)
    if scores[category] == 0:
        category = "unknown"
    keywords = [
        keyword for keyword, terms in KEYWORD_RULES.items()
        if any(_matches(text, term) for term in terms)
    ]
    if category != "unknown":
        keywords.append(category)
    area = None
    for candidates in (NEIGHBORHOODS, CITIES):
        found = [name for name in candidates if name in text]
        if found:
            area = min(found, key=text.index)
            break
    return AnalyzedContent(
        category=category, keywords=keywords, area=area,
        activity=ACTIVITIES.get(category),
    )
