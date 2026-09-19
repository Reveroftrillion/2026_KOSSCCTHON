"""누적 분석 결과를 이용한 취향 계산과 MVP 메모리 저장소."""

from collections import Counter
from typing import Iterable

if __package__:
    from .schemas import AnalyzedContent, PreferenceProfile
else:
    from schemas import AnalyzedContent, PreferenceProfile


def calculate_preferences(
    user_id: int, analyzed_contents: Iterable[AnalyzedContent],
) -> PreferenceProfile:
    """카테고리 및 키워드 등장 콘텐츠 수를 전체 콘텐츠 수로 나눈다.

    키워드는 콘텐츠당 한 번만 센다. unknown도 분모와 카테고리에 포함한다.
    빈 입력은 빈 프로필을 반환하며, 반올림으로 비율 합이 1과 다를 수 있다.
    """
    contents = list(analyzed_contents)
    profile = PreferenceProfile(user_id=user_id)
    if not contents:
        return profile
    categories = Counter(item.category for item in contents)
    keywords = Counter(keyword for item in contents for keyword in set(item.keywords))
    profile.category_preferences = {
        category: round(count / len(contents), 3)
        for category, count in sorted(categories.items())
    }
    profile.keyword_preferences = {
        keyword: round(count / len(contents), 3)
        for keyword, count in sorted(keywords.items())
    }
    return profile


class PreferenceDB:
    """사용자별 분석 이력을 보관한다. 프로세스 종료 시 데이터는 사라진다.

    update에는 새로 분석한 콘텐츠만 전달한다. 같은 콘텐츠를 다시 전달하면
    별도 입력으로 누적된다. 실제 DB 연동 시 이 저장 계층을 교체할 수 있다.
    """

    def __init__(self) -> None:
        """빈 사용자별 분석 이력 저장소를 만든다."""
        self._contents: dict[int, list[AnalyzedContent]] = {}

    def update(
        self, user_id: int, analyzed_contents: Iterable[AnalyzedContent],
    ) -> PreferenceProfile:
        """새 분석 결과를 누적하고 전체 이력으로 프로필을 갱신한다."""
        user_id = PreferenceProfile(user_id=user_id).user_id
        incoming = [
            AnalyzedContent.model_validate(item).model_copy(deep=True)
            for item in analyzed_contents
        ]
        self._contents.setdefault(user_id, []).extend(incoming)
        return calculate_preferences(user_id, self._contents[user_id])

    def get_profile(self, user_id: int) -> PreferenceProfile:
        """사용자의 현재 프로필을 조회한다. 이력이 없으면 빈 프로필이다."""
        return calculate_preferences(user_id, self._contents.get(user_id, []))

    def get_all_profiles(self) -> dict[int, PreferenceProfile]:
        """사용자 ID를 키로 전체 취향 DB의 스냅샷을 반환한다."""
        return {user_id: self.get_profile(user_id) for user_id in sorted(self._contents)}
