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

## 다음 URL 연동 위치

향후 YouTube Shorts 메타데이터 수집기를 `analyze_content()` 앞에 연결한다.
URL에서 얻은 `title`, `description`에 `user_id`, `url`을 붙여 `ContentInput`으로
전달하면 이후 분석·취향 계산 코드를 재사용할 수 있다. 현재 URL은 수집하지 않는다.

국민대 provider에 대한 실제 연결 성공 여부는 유효한 `LLM_API_KEY`를 설정한 뒤
`[Parser] llm` 출력으로 확인한다. 모의 HTTP 테스트는 서버 연결 검증을 대신하지 않는다.
