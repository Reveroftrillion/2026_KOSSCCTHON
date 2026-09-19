# TripClip 콘텐츠 취향 분석 MVP

Python 3.10 이상. 저장소 루트에서 실행한다.

```powershell
python -m pip install -r ai/preference_analyzer/requirements.txt
python ai/preference_analyzer/sample.py
python -m unittest ai.preference_analyzer.test_pipeline -v
```

## 분석 흐름

`ContentInput` → `content_parser.analyze_content()` → `llm_parser` →
`AnalyzedContent` → `PreferenceDB.update()` → 사용자별 취향 프로필.

`LLM_API_KEY`가 없거나 공백이면 LLM을 호출하지 않는다. SDK 미설치,
API 오류, 타임아웃, 잘못된 JSON, 허용되지 않은 카테고리, 빈 키워드,
응답 거절/미완료 등은 `rule_parser.analyze_with_rules()`로 fallback한다.
콘솔의 `[Parser] llm` 또는 `[Parser] rule-based`로 실제 경로를 확인한다.
잘못된 사용자 ID 등 입력 자체의 검증 오류는 기존처럼 호출자에게 전달된다.

## 환경변수와 두 가지 실행 모드

- `LLM_API_KEY`: 국민대 AI 플랫폼 키. OS 또는 현재 터미널 환경변수로 설정한다.
- `LLM_BASE_URL`: 기본값 `https://ai.cs.kookmin.ac.kr/v1`.
- `LLM_MODEL`: 기본값 `claude-sonnet-4-5`. `claude-sonnet-4-6`으로 변경 가능하다.
- URL과 모델 설정이 없거나 공백이면 기본값을 사용한다. 기존 `OPENAI_*` 변수는 사용하지 않는다.
- `.env` 파일을 생성하거나 자동 로드하지 않는다.
- 요청 타임아웃은 15초, SDK 자동 재시도는 0회다. 실패한 콘텐츠마다 규칙 분석으로 전환한다.

키 없는 모드를 PowerShell에서 확인하려면 현재 세션의 변수를 제거한 뒤 실행한다.

```powershell
Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
python ai/preference_analyzer/sample.py
```

LLM 모드는 `LLM_API_KEY`를 안전하게 설정한 터미널에서 아래 명령을 실행한다.

```powershell
$env:LLM_BASE_URL = "https://ai.cs.kookmin.ac.kr/v1"
$env:LLM_MODEL = "claude-sonnet-4-5"
python ai/preference_analyzer/sample.py
```

OpenAI SDK는 호환 클라이언트로만 사용한다. `base_url`을 명시하여 국민대의
`POST /v1/chat/completions`에 system/user 메시지를 전송한다. 공식 OpenAI endpoint나
Responses API는 사용하지 않는다. `response_format`도 전송하지 않으며, JSON 반환
프롬프트 → `LLMOutput` 검증 → `AnalyzedContent` 정규화 순서로 처리한다.
JSON 전체를 감싼 코드 블록은 허용하고, 잘린 응답이나 잘못된 JSON은 fallback한다.

실제 API 호출에는 계정 권한과 네트워크가 필요하다. 테스트는 SDK 호출을 모의 처리하며
실제 API 키나 네트워크를 사용하지 않는다. 실제 SDK와 모의 HTTP 전송 계층으로
국민대 요청 URL·모델·헤더 및 sample의 8개 LLM 분석 경로도 검증한다.
의존성은 기존 `pydantic`과 `openai` 그대로다.

## 호환성과 정규화

- `sample.py`, `preference.py`와 공개 함수의 호출 방식은 유지한다.
- 원래 Mock 8개의 규칙 분석 취향 비율을 회귀 테스트로 확인한다.
- 카테고리와 별칭은 `schemas.py`에서 관리한다. `restaurant` → `food`.
  기존 `unknown`은 호환성 때문에 유지하며 새 분류에 `other`도 지원한다.
- 새 필드 `place_name`, `recommended_time`, `user_id`, `title`은 기본값이 null이다.
  진입점은 사용자 ID와 제목을 원본 입력에서 채운다.
- 키워드는 소문자화, 별칭 통합, 중복 제거, 최대 7개 제한을 적용한다.
  최대 30자·3단어까지 허용하며 근거가 부족하면 3개 미만도 허용한다.
- 원문에 없는 장소명/지역은 null로 제거한다. 추천 시간은 명시된 시간만 추출하도록
  프롬프트로 제한한다. 의미 해석의 정확성은 별도 실데이터 평가가 필요하다.
- 카테고리/키워드 모두 등장 콘텐츠 수 ÷ 전체 콘텐츠 수, 소수점 3자리다.
  키워드 비율 합은 1일 필요가 없다. 저장소는 메모리 기반이며 종료하면 초기화된다.
  같은 콘텐츠를 다시 추가하면 별도 입력으로 누적된다.

## YouTube URL 분석

```powershell
python -m pip install -r ai/preference_analyzer/requirements.txt
python ai/preference_analyzer/youtube_sample.py "https://www.youtube.com/shorts/VIDEO_ID" --user-id 1
python -m unittest ai.preference_analyzer.test_pipeline ai.preference_analyzer.test_youtube -v
```

`VIDEO_ID`는 실제 11자리 영상 ID로 바꾼다. `youtube.com/shorts/`,
`www.youtube.com/shorts/`, `youtube.com/watch?v=`, `youtu.be/`를 지원한다.
URL 호스트·경로·ID를 검증하며, 공유 쿼리와 무관하게 같은 ID를 추출한다.
URL 형식만으로 해당 영상이 Shorts인지는 판별하지 않는다.

- `YOUTUBE_API_KEY` 있음: 공식 Data API v3 `videos.list(part=snippet, id=...)`.
- 키 없음 또는 공백: 공식 YouTube oEmbed. 내부 요청은 동일 ID의 watch URL로 정규화한다.
- Data API 오류에는 명확한 오류를 반환한다. 키가 있는 경우 oEmbed로 재시도하지 않는다.
- oEmbed는 제목·채널·썸네일만 수집한다. 설명과 태그는 빈 값이므로 분석 근거가 제한된다.
- 수집 요청에는 10초 타임아웃을 적용하고 리다이렉트는 따르지 않는다.
- `ContentInput.tags`는 기본값이 빈 배열인 선택 필드다. Claude와 규칙 분석 모두 활용한다.
- 다운로드·HTML 크롤링·영상 분석은 하지 않는다. 메타데이터를 얻지 못하면 DB를 갱신하지 않는다.
- CLI는 사용자에게 오류를 출력하고 종료 코드 1을 반환한다. 성공 시 0을 반환한다.
  제목이 없으면 분석을 중단하고, 설명·태그가 없어도 제목으로 진행한다.

Backend용 진입점은 다음과 같다. 반환값은 JSON 직렬화 가능한 dict다.

```python
from ai.preference_analyzer import MetadataError, PreferenceDB, analyze_youtube_url, process_youtube_url

db = PreferenceDB()  # 여러 요청에서 누적하려면 같은 인스턴스를 재사용한다.
try:
    result = process_youtube_url(user_id=1, url=youtube_url, preference_db=db)
    # result: metadata, analysis, preference_profile
except MetadataError as error:
    message = str(error)  # URL/수집 실패를 사용자에게 안내할 수 있는 메시지
```

`analyze_youtube_url(user_id, url)`은 DB를 갱신하지 않고 `metadata`, `analysis`만 반환한다.
잘못된 사용자 ID는 Pydantic `ValidationError`이며, 수집 오류는 `MetadataError`다.
`process_youtube_url()`은 분석 완료 후 기존 DB의 `update()`를 한 번 호출한다.
CLI는 실행마다 새 메모리 DB를 만든다. 동일 URL을 재입력하면 기존 정책대로 누적된다.

추가 직접 의존성은 `httpx>=0.27,<1.0`이다. 기존 `LLM_*` 환경변수는 그대로 사용한다.
새 `.env` 파일은 생성하지 않는다.

검증: 기존 14개 + YouTube 13개 = 27개 모의 테스트 통과.
실제 공개 watch URL `https://www.youtube.com/watch?v=jNQXAC9IVRw`에서 oEmbed 수집과
rule-based 프로필 생성에 성공했다. 이번 작업 환경에는 API 키가 없어 실제 Data API와
Claude 호출은 검증하지 않았다. Shorts URL 파싱 및 Claude 연결은 모의 테스트로 검증했다.

수집 참고: [YouTube videos.list 공식 문서](https://developers.google.com/youtube/v3/docs/videos/list),
[oEmbed 명세](https://oembed.com/).

국민대 provider에 대한 실제 연결 성공 여부는 유효한 `LLM_API_KEY`를 설정한 뒤
`[Parser] llm` 출력으로 확인한다. 모의 HTTP 테스트는 서버 연결 검증을 대신하지 않는다.
