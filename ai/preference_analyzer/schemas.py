"""분석기와 취향 계산기가 공유하는 Pydantic 입출력 모델."""

import re
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

Category = Literal[
    "cafe", "food", "exhibition", "shopping", "outdoor", "activity",
    "sightseeing", "nightlife", "accommodation", "other", "unknown",
]
# unknown은 기존 규칙 분석 결과와의 호환성을 위해 유지한다.
CATEGORIES = get_args(Category)
CATEGORY_ALIASES = {"restaurant": "food", "coffee": "cafe", "museum": "exhibition", "hotel": "accommodation"}
KEYWORD_ALIASES = {
    "photography": "photo", "photos": "photo", "사진": "photo",
    "dating": "date", "데이트": "date", "desserts": "dessert", "디저트": "dessert",
    "카페": "cafe", "café": "cafe", "조용": "quiet", "전시": "exhibition",
    "artwork": "art", "indoors": "indoor", "outdoors": "outdoor",
    "restaurant": "food", "맛집": "food",
}


class ContentInput(BaseModel):
    """URL 없이도 제목과 설명만으로 분석할 수 있는 입력 콘텐츠."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int = Field(gt=0)
    url: HttpUrl | None = None
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class YouTubeMetadata(BaseModel):
    """YouTube 공식 API에서 수집한 공개 메타데이터."""

    model_config = ConfigDict(str_strip_whitespace=True)

    platform: Literal["youtube"] = "youtube"
    url: str
    video_id: str
    title: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    channel_title: str | None = None
    thumbnail_url: str | None = None


class AnalyzedContent(BaseModel):
    """규칙 기반 분석기와 향후 LLM 분석기가 반환할 공통 결과."""

    category: Category
    keywords: list[str] = Field(default_factory=list)
    area: str | None = None
    activity: str | None = None
    place_name: str | None = None
    recommended_time: Literal["morning", "afternoon", "evening", "night"] | None = None
    user_id: int | None = Field(default=None, gt=0)
    title: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        """알려진 별칭만 정규화하고 허용 목록 밖의 값은 검증에서 거부한다."""
        if isinstance(value, str):
            value = value.strip().lower()
            return CATEGORY_ALIASES.get(value, value)
        return value

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        """짧은 키워드를 소문자·별칭 정규화하고 중복 없이 최대 7개 유지한다."""
        result = []
        for value in values:
            keyword = "_".join(value.strip().lower().split())
            keyword = KEYWORD_ALIASES.get(keyword, keyword)
            if (re.fullmatch(r"[^\W_]+(?:[_-][^\W_]+){0,2}", keyword)
                    and len(keyword) <= 30 and keyword not in result):
                result.append(keyword)
        return result[:7]


class PreferenceProfile(BaseModel):
    """사용자별 카테고리 및 키워드 선호 비율."""

    user_id: int = Field(gt=0)
    category_preferences: dict[str, float] = Field(default_factory=dict)
    keyword_preferences: dict[str, float] = Field(default_factory=dict)
