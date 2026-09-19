"""분석기와 취향 계산기가 공유하는 Pydantic 입출력 모델."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Category = Literal["cafe", "exhibition", "food", "shopping", "outdoor", "unknown"]


class ContentInput(BaseModel):
    """URL 없이도 제목과 설명만으로 분석할 수 있는 입력 콘텐츠."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int = Field(gt=0)
    url: HttpUrl | None = None
    title: str = ""
    description: str = ""


class AnalyzedContent(BaseModel):
    """규칙 기반 분석기와 향후 LLM 분석기가 반환할 공통 결과."""

    category: Category
    keywords: list[str] = Field(default_factory=list)
    area: str | None = None
    activity: str | None = None


class PreferenceProfile(BaseModel):
    """사용자별 카테고리 및 키워드 선호 비율."""

    user_id: int = Field(gt=0)
    category_preferences: dict[str, float] = Field(default_factory=dict)
    keyword_preferences: dict[str, float] = Field(default_factory=dict)
