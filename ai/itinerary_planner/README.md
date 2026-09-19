# AI1 → AI2 그룹 취향 연결

저장소 루트에서 사용한다. 새로운 의존성은 없다.

```python
from ai.preference_analyzer import export_all_preference_profiles
from ai.itinerary_planner.group_preference import build_group_preferences

profiles = export_all_preference_profiles(preference_db)
group = build_group_preferences(profiles)
```

AI1의 JSON 파일도 동일한 배열 계약을 사용한다.

```python
from ai.itinerary_planner.group_preference import load_preference_profiles, build_group_preferences

profiles = load_preference_profiles("ai/preference_analyzer/sample_group_preferences.json")
group = build_group_preferences(profiles)
```

입력은 `user_id`, `category_preferences`, `keyword_preferences`를 가진 객체의 배열이다.
ID는 중복 없는 양의 정수, 점수는 0~1의 유한한 숫자여야 한다. 추가 evidence 필드는
이 단계에서 사용하지 않는다. 이름·점수는 정규화하거나 재분배하지 않는다.

반환 구조 예시:

```json
{
  "users": {
    "1": {"category_preferences": {"cafe": 0.5}, "keyword_preferences": {"photo": 0.6}},
    "2": {"category_preferences": {"cafe": 0.2}, "keyword_preferences": {"photo": 0.3}},
    "3": {"category_preferences": {}, "keyword_preferences": {}}
  },
  "group_category_preferences": {"cafe": 0.233},
  "group_keyword_preferences": {"photo": 0.3}
}
```

사용자별 점수는 원본 그대로 보존한다. 그룹 점수는 각 점수의 합 / 전체 사용자 수이며
없는 취향은 0으로 계산한다. 빈 프로필의 사용자도 분모에 포함한다. 그룹 결과만 소수점
3자리로 반올림한다. 빈 배열은 세 필드 모두 빈 객체를 반환한다. 키워드 합을 1로 정규화하지 않는다.

기존 `analyze_preferences()`도 AI1 배열을 받으면 위 세 필드를 기존 공통/개별 취향
분석 결과에 추가한다. `balance_group_preferences()`도 이를 보존한다.
기존 AI2 `sample_input.json`의 사용자 이름 기반 dict/list 입력은 기존 결과 형식을 유지한다.
그 legacy 형식은 점수가 없는 목록도 포함하므로 임의 점수를 부여하지 않는다.
`itinerary_generator.py`는 아래의 장소 적합도와 균형 기반 선택 흐름을 사용한다.

```powershell
# AI1 샘플을 읽고 사용자별 점수 및 그룹 평균 출력
python ai/itinerary_planner/group_preference.py ai/preference_analyzer/sample_group_preferences.json
# 기존 AI2 샘플 동작 유지
python ai/itinerary_planner/group_preference.py
python ai/itinerary_planner/itinerary_generator.py
# 통합 테스트
python -m unittest ai.itinerary_planner.test_group_preference ai.preference_analyzer.test_pipeline ai.preference_analyzer.test_youtube ai.preference_analyzer.test_exports -v
```

## 장소 점수 → 균형 선택 → 일정

```python
from ai.preference_analyzer import export_all_preference_profiles
from ai.itinerary_planner.itinerary_generator import generate_itinerary

conditions = {
    "region": "성수", "date": "토요일", "time": "13:00 ~ 20:00",
    "user_conditions": ["저녁 식사 포함", "1인 예산 50,000원 이하"],
}
result = generate_itinerary(
    conditions,
    profiles=export_all_preference_profiles(preference_db),
    place_candidates=places,
)
```

Backend의 향후 Maps 결과를 `place_candidates`로 전달한다. 각 장소에 중복 없는 문자열
`place_id`, `name`, `category`, 문자열 배열 `keywords`가 필요하다. 카테고리·키워드는 AI1과
같은 소문자 표준명을 사용한다. 좌표는 보관할 수 있지만 현재 거리 계산에 사용하지 않는다.
후보는 Backend에서 여행 지역에 맞게 준비한다. 지역·운영시간·가격 필터링은 수행하지 않는다.

인자를 생략하면 AI1 `sample_group_preferences.json`과 AI2 `sample_places.json`을 사용한다.
운영 연동에서는 두 인자를 명시한다. 기존 sample_input의 `personal_preference_db` 및
`group_saved_places`는 새 일정 생성의 점수·장소 입력으로 사용하지 않으며 여행 조건만 읽는다.
`sample_places.json`의 이름·좌표는 테스트용 가상 후보이며 실제 장소 정보의 정확성을 보장하지 않는다.

- `place_scoring.score_user_place()`: `0.6 × category_score + 0.4 × keyword_score`.
  keyword_score는 사용자 취향 dict에 존재하는 장소 키워드들의 평균이다. 중복 키워드는
  한 번만 세고, 매칭이 없으면 0이다. 장소의 모든 키워드 수로 나누지는 않는다.
- `place_scoring.score_places()`: 각 장소의 사용자별 점수와 전체 사용자 평균 `group_score` 계산.
- `place_selector.select_places()`: 후보 추가 후 예상 coverage를 구하고,
  `0.7 × group_score + 0.3 × min(projected_coverage)`가 가장 큰 장소를 순차 선택한다.
  동점이면 place_id 오름차순으로 결정한다. 최대 4개이며 같은 장소는 반복하지 않는다.
- coverage는 선택된 장소 중 각 사용자의 최대 점수다. 초기값은 0이며 빈 후보는 빈 일정과
  사용자별 0 coverage를 반환한다. 사용자도 없으면 빈 일정·빈 coverage를 반환한다.
- 시간은 선택 순서대로 `[시작, 종료)`에 균등 배치한다. 13:00~20:00, 4개이면
  13:00 / 14:45 / 16:30 / 18:15이다. 같은 날의 유효한 시간 범위만 받는다.
- `related_users`는 장소 평균 이상인 사용자 ID의 정수 배열이다. 모든 점수가 0이면
  조건상 모든 사용자가 포함되지만 reason은 긍정적 매칭 근거가 없다고 명시한다.
- `build_reason()`은 매칭 category와 keywords로 설명을 생성한다. LLM을 호출하지 않는다.
- 계산·선택은 반올림 전 숫자를 쓰고 최종 점수·coverage 출력만 소수점 3자리로 반올림한다.
  coverage는 만족 확률이나 전체 취향 반영 비율이 아니라 최대 장소 적합도 지표다.
- 가격·식사 조건은 `unverifiable_conditions`에 유지한다. 최소 반영도 보장, 동선 최적화,
  카테고리 다양성 강제 등의 추가 제약은 없다.

기존 사용자 취향 순서로 category를 cycling하던 로직은 제거했다.
`generate_schedule()`은 이제 **선택·채점이 완료된 장소 배열**을 받는다.
AI1 코드와 그룹 평균 계산은 수정하지 않았다.

```powershell
python ai/itinerary_planner/itinerary_generator.py
python -m unittest ai.itinerary_planner.test_itinerary ai.itinerary_planner.test_group_preference ai.preference_analyzer.test_pipeline ai.preference_analyzer.test_youtube ai.preference_analyzer.test_exports -v
```

샘플 결과: 13:00 성수 디저트 카페(cafe), 14:45 서울숲(outdoor),
16:30 성수 전시회(exhibition), 18:15 성수 산책 전망대(sightseeing).
coverage: 사용자 1 = 0.467, 사용자 2 = 0.550, 사용자 3 = 0.533.
