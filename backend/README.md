# Backend DB 정합성 및 실행 안내

```powershell
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
python -m unittest backend.tests.test_backend -v
```

Swagger: `http://localhost:8000/docs`. AI1 콘텐츠 분석과 AI2 일정 생성 API를 포함한다.
모든 명령은 프로젝트 루트에서 실행한다. `python -m backend.main`도 사용할 수 있다.
의존성은 기존 루트 `requirements.txt`를 유지한다.

## DB 환경변수

`.env.example`은 설정 항목 예시이며 자동으로 로드하지 않는다. OS 또는 실행 터미널에서 설정한다.
`DB_HOST=localhost`, `DB_PORT=3306`, `DB_USER=root`, `DB_NAME=tripclip`이 기본값이다.
`DB_PASSWORD`의 기본값은 빈 문자열이다. 사용하는 MySQL 계정의 실제 값은 환경변수로만 설정한다.
SQLAlchemy URL.create를 사용하므로 비밀번호 특수문자를 직접 URL 인코딩할 필요가 없다.
실제 `.env`는 기존 `.gitignore`에서 제외한다.

기존 소스에 포함됐던 MySQL 비밀번호는 제거했다. Git 과거 이력까지 삭제한 것은 아니므로
해당 자격증명이 실제 사용 중이었다면 DB에서 교체해야 한다.

## 현재 DB 확인 및 마이그레이션

먼저 올바른 DB에 접속한 뒤 확인한다.

```sql
SELECT DATABASE();
SHOW COLUMNS FROM users;
SHOW COLUMNS FROM trips;
SHOW COLUMNS FROM trip_members;
SHOW COLUMNS FROM user_preferences;
SHOW CREATE TABLE trips;
```

신규 빈 DB에는 `backend/db/schema.sql`을 적용한다. **schema.sql 수정은 기존 테이블을 자동 변경하지 않는다.**
`backend.database.init_db()`의 SQLAlchemy Base에는 현재 모델이 등록되지 않아 이 SQL 스키마를 만들지 않는다.
기존 DB는 백업 및 컬럼 확인 후 `backend/db/migrations/001_backend_schema_alignment.sql`에서 필요한 문장만 적용한다.
이 파일은 기존 원본 스키마를 기준으로 하며, 이미 컬럼이 있는 DB에 전체 재실행하면 오류가 난다.
MySQL DDL은 자동 commit될 수 있다.

기존 원본 스키마에 필요한 주요 변경:

```sql
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE trips ADD COLUMN description TEXT;
UPDATE users SET password_hash = '!reset-required' WHERE password_hash IS NULL;
ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NOT NULL;
```

기존 사용자에게 비밀번호가 없었다면 공통 기본 비밀번호를 발급하지 않는다.
`!reset-required`는 로그인용 hash가 아닌 재설정 필요 표식이다. 기존 SHA-256 hash를
SQL로 bcrypt로 변환할 수는 없다. 향후 로그인 구현 시 비밀번호 재설정 또는 안전한
로그인 시점 재해싱 절차가 필요하다. 이번 변경은 신규 가입의 bcrypt 저장까지다.

trips에 `user_id`만 존재하고 `owner_user_id`가 없는 DB에서만 다음을 실행한다(MySQL 8+).

```sql
ALTER TABLE trips RENAME COLUMN user_id TO owner_user_id;
```

두 컬럼이 모두 있으면 데이터와 외래키를 먼저 대조해 수동 정리한다.
**trip_members.user_id는 변경하지 않는다.** profile_image_url 및 기존 timestamp 필드도 유지한다.

## API 계약

회원가입 예:

```json
{"name":"테스트유저","email":"test@example.com","password":"example-password"}
```

가입 응답의 `user_id`를 아래 `owner_user_id`에 넣는다. POST 및 PUT 여행 요청 형식은 동일하다.

```json
{
  "trip_name": "성수 여행",
  "region": "성수",
  "start_date": "2026-09-20",
  "end_date": "2026-09-20",
  "owner_user_id": "회원가입 응답의 user_id",
  "day_start_time": "13:00:00",
  "day_end_time": "20:00:00",
  "description": ""
}
```

여행 조회 응답도 `owner_user_id`를 사용한다. `/api/users/{user_id}/trips`는 해당 사용자가
소유한 여행 목록이며 가입한 모든 그룹 목록을 뜻하지 않는다. PUT의 owner_user_id는
존재하는 사용자여야 하고 저장된 방장도 갱신한다. 현재 인증/인가 계층은 없으므로
운영 배포 전에 방장 변경·수정·삭제 권한 확인을 별도로 구현해야 한다.

테스트는 전체 schema.sql을 SQLite 문법으로 조정하여 실제 HTTP와 SQL을 검증한다.
기존 10개 API 테스트와 신규 서비스 테스트를 포함하며 실제 MySQL 엔진·동시성·마이그레이션
실행 검증을 대신하지 않는다. 외부 API 호출은 mock으로 대체한다.

## AI 영속화 MVP (Phase 1~24)

멤버, 숏폼, 개인·그룹 취향 조회, mock 장소, 실제 AI2 함수 실행, 일정 저장·조회까지 구현했다.
실제 Maps provider만 향후 연결 지점으로 남겨두었다. AI 알고리즘 파일은 변경하지 않았다.

```text
backend/
  main.py                 기존 User/Trip + router 등록/안전한 오류 응답
  database.py
  routers/{members,shortforms,preferences,itineraries}.py
  services/{common,preference_service,place_service,itinerary_service}.py
  db/schema.sql
  db/migrations/001_backend_schema_alignment.sql
  db/migrations/002_ai_persistence.sql
  tests/test_backend.py
  tests/test_members.py
  tests/test_shortforms.py
  tests/test_preferences.py
  tests/test_itineraries.py
  tests/test_service_flow.py
```

### DB 변경 및 migration

기존 DB에는 001 적용 상태를 확인한 뒤 **002_ai_persistence.sql을 한 번 적용**한다.
신규 DB에는 최신 schema.sql만 적용하며 002를 중복 적용하지 않는다.
002는 `shortform_contents` 생성, 기존 방장 멤버 backfill, 다음 컬럼 추가를 수행한다.

- `trip_itineraries.preference_coverage`, `preference_reflection`, `result_json` (JSON)
- `itinerary_places.user_scores` (JSON), `group_score` (DOUBLE)
- 기존 `preference_reflection_rates`는 삭제하거나 재해석하지 않고 보존한다.

기존 데이터 백업 후 `SHOW COLUMNS`, `SHOW CREATE TABLE`로 적용 여부를 확인한다.
마이그레이션은 앱 실행 시 자동 적용하지 않는다. MySQL 8/InnoDB와 utf8mb4를 권장한다.
기존 일정에 result_json이 없으면 GET은 `legacy: true`와 저장된 ID·summary를 반환한다.

### UUID ↔ AI 정수 ID

DB와 HTTP의 실제 user_id는 항상 Backend UUID 문자열이다. AI1 호출에는 해당 문자열의
UTF-8 바이트를 양의 정수로 인코딩한 값만 전달한다 (`int.from_bytes(...) + 1`).
이는 사용자별 결정적 변환이며 고정 임시 ID나 영속 ID 변경이 아니다. AI1에 입력한 정수는
저장 전에 버리고 검증된 Backend UUID를 분석 응답과 DB 저장의 source of truth로 사용한다.
기존 Backend의 문자열 ID 계약도 유지한다.

AI2는 요청마다 멤버 ID 정렬 순서대로 1..N 매핑을 만든다. profile의 category·keyword 점수는
그대로 전달한다. 반환의 `user_scores`, `related_users`, `preference_coverage`,
`preference_reflection`, reason의 사용자 참조를 원래 UUID로 복원한다.
GET trip preferences는 UUID 배열이므로 **AI2 직접 호출이 아니라 Backend adapter를 거쳐야 한다.**

### 취향 계산·트랜잭션

서버 전역 PreferenceDB는 없다. 모든 여행에서 해당 사용자 UUID로 저장된 shortform_contents
전체를 읽고 AI1 `calculate_preferences()`를 재사용한다. 카테고리/키워드 등장 콘텐츠 수 ÷ 전체 수,
키워드 콘텐츠당 한 번, 소수점 3자리라는 기존 의미를 유지한다.
DB mapping은 category_preferences → category_scores, keyword_preferences → tag_scores다.
사용자당 한 행을 INSERT/UPDATE하고 updated_at을 갱신한다.

- Trip 생성 + 방장 멤버 등록은 같은 commit. 방장 변경 시 새 방장도 멤버로 등록한다.
- Shorts는 trip/user/member/중복 검증 → 읽기 transaction 해제 → AI1 실행 → write transaction에서
  재검증 → content INSERT + preference 갱신 → commit. 실패 시 전체 rollback한다.
- URL은 video ID 기반 watch URL로 정규화한다. 같은 trip/user/video의 shorts·watch·youtu.be
  주소는 중복으로 보며 409를 반환한다. 다른 여행의 같은 영상은 별도 저장 이력으로 센다.
  canonical URL은 ASCII이고 MySQL url 컬럼은 ascii_bin collation을 사용하여 영상 ID의 대소문자를 구분한다.
- AI1의 정상 rule fallback은 유효한 분석 성공이다. metadata 실패나 AI1 함수 자체의 예외는
  502이며 저장하지 않는다. LLM 실패 때 fallback을 제거하지 않는다.
- content 삭제와 trip 삭제 시 남은 콘텐츠로 해당 사용자 취향을 재계산한다. 마지막 삭제는 `{}`.
  멤버 탈퇴는 저장 이력을 삭제하지 않으며, trip preference 조회 대상에서만 제외한다.
- MySQL에서 사용자 row lock으로 preference 갱신을 직렬화하고 trip row lock으로 멤버/일정 변경을
  조정한다. 외부 호출 중에는 DB write transaction을 보유하지 않는다.
- AI2 결과 확보 후 trip/user lock, trip 조건·멤버 preference snapshot 재검증을 수행한다.
  생성 중 데이터가 바뀌면 409로 재시도를 요청한다.
- 장소 upsert + 일정 본문 + 상세 장소는 한 transaction. 중간 실패 시 기존 일정까지 복구한다.

### 장소와 일정 저장 정책

KAKAO_REST_API_KEY가 없으면 AI2 sample_places.json을 읽고 `place_source: mock`으로 명시한다.
이 후보는 가상 데이터이며 요청 지역과 실제 위치가 일치함을 보장하지 않는다.
키가 있으면 별도 `search_provider_places()`로 위임하지만 **현재 실제 provider 미구현이므로 503**이다.
실제 Kakao 호출은 하지 않는다. 제공자 구현 시 region과 profiles로 후보를 준비하고 기존
`place_id/name/category/keywords/lat/lng` 계약과 dictionary 기반 category 정규화를 사용한다.

선택 장소의 provider/mock ID는 source로 namespacing한 UUID5로 바꾸어 places에 upsert한다.
itinerary_places는 이 실제 DB UUID를 FK로 사용한다. 반환 place_id도 DB UUID다.
같은 trip/day_number는 새 이력을 무한 생성하지 않고 **원자적으로 교체**하며 itinerary_id는 유지한다.
day_number는 요청 날짜 − 여행 시작 날짜 + 1이다. 요청 날짜는 여행 범위 내여야 한다.
MySQL TIME이 timedelta로 반환되는 경우도 HH:MM으로 변환하며 초가 0이 아닌 값은 400이다.
방문 종료 시간은 다음 stop 시작 또는 여행 일 종료 시간이며 실제 이동/체류 검증이 아니다.
조회는 result_json snapshot을 반환하므로 이후 places/취향이 바뀌어도 생성 당시 결과가 보존된다.

### 새 endpoint

| Method | Path | 반환 |
|---|---|---|
| POST/GET | `/api/trips/{trip_id}/members` | 등록 / 이름·joined_at 포함 목록 |
| DELETE | `/api/trips/{trip_id}/members/{user_id}` | 탈퇴 (현재 방장은 409) |
| POST/GET | `/api/trips/{trip_id}/shortforms` | 분석·취향 / 저장 콘텐츠 목록 |
| DELETE | `/api/trips/{trip_id}/shortforms/{content_id}` | 삭제 후 취향 |
| GET | `/api/users/{user_id}/preferences` | UUID·category_preferences·keyword_preferences |
| GET | `/api/trips/{trip_id}/preferences` | 현재 멤버 전원 프로필 배열 (빈 취향 포함) |
| POST | `/api/trips/{trip_id}/itinerary` | 일정 snapshot·coverage·reflection |
| GET | `/api/trips/{trip_id}/itineraries` | 일자 순 전체 일정 배열 |
| GET | `/api/trips/{trip_id}/itineraries/{itinerary_id}` | 특정 일정 snapshot |

검증 실패는 400/422, non-member는 403, 없는 자원은 404, 중복·상태 충돌은 409,
분석/provider 오류는 502, 미구현 지도 provider는 503, DB 오류는 500이다.
새 오류 응답은 provider 원문이나 키·SQL parameter를 포함하지 않는다.

### Swagger 실제 테스트 순서

1. `POST /api/users`를 세 번 호출: `{"name":"User 1","email":"user1@example.com","password":"example-password"}`
   (이름·이메일을 각각 변경하고 반환 UUID 3개를 보관).
2. `POST /api/trips`: 위 여행 예시의 owner_user_id에 첫 UUID를 넣고 trip_id를 보관.
3. `POST /api/trips/{trip_id}/members` 두 번: `{"user_id":"두 번째 또는 세 번째 UUID"}`.
4. `GET /api/trips/{trip_id}/members`: 방장 포함 3명 확인.
5. 사용자별 `POST /api/trips/{trip_id}/shortforms` 2~3회:
   `{"user_id":"사용자 UUID","url":"https://www.youtube.com/shorts/실제영상ID"}`.
6. `GET /api/trips/{trip_id}/shortforms`: category, keywords, nullable place_name 확인.
7. `GET /api/trips/{trip_id}/preferences` 및 `/api/users/{user_id}/preferences`.
8. `POST /api/trips/{trip_id}/itinerary`: `{"date":"2026-09-20","user_conditions":[]}`.
9. `GET /api/trips/{trip_id}/itineraries` 및 `/{itinerary_id}`로 저장 결과 확인.
10. 필요 시 shortform DELETE 후 해당 사용자 preference 재계산 확인.

### 실행 환경과 검증

루트 requirements.txt 하나로 AI와 Backend 의존성을 설치한다. .env.example은 예시이며
실제 .env 자동 로딩은 하지 않는다. DB 변수는 실제 MySQL 연결에 필요하고 기본값은 위 설명과 같다.
LLM_API_KEY는 실제 Claude 호출 시 필요(없으면 rule fallback), LLM_BASE_URL과 LLM_MODEL은 기존
국민대 기본값, YOUTUBE_API_KEY는 선택(없으면 oEmbed), KAKAO_REST_API_KEY는 현재 비워둔다.

```powershell
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
python -m unittest discover -s backend/tests -t . -v
python -m unittest ai.preference_analyzer.test_pipeline ai.preference_analyzer.test_youtube ai.preference_analyzer.test_exports ai.itinerary_planner.test_group_preference ai.itinerary_planner.test_itinerary ai.itinerary_planner.test_ai2_pipeline ai.itinerary_planner.test_generic_keywords -v
```

AI는 namespace package여서 루트 unittest discover만으로 AI 테스트가 빠질 수 있으므로 위 두 명령을
모두 실행한다. smoke test는 3명 가입 → 여행/멤버 → 6개 콘텐츠 → DB 취향 → mock 장소 → 실제 AI2
→ 일정 저장·조회까지 검사한다. 실제 MySQL·Claude·YouTube·Kakao는 이 테스트에서 호출하지 않는다.
실제 환경에서 migration 적용, provider 자격증명 연결, MySQL 동시성 검증은 별도로 수행해야 한다.
현재 사용자 UUID는 요청값이며 인증된 사용자 확인은 없다. 인증·권한, rate limit, 실제 지도 연동은
운영 배포 전에 필요한 후속 작업이다.


## ?? MySQL ??? ??? ??

??? MySQL 8.x / InnoDB / utf8mb4?. ?? ???? ??? ??? ?? SQL?driver ?? ????,
??? MySQL ???? JSON/TIME/DECIMAL/???/upsert round trip? ??? ? ??.

| ?? | ?? ?? |
|---|---|
| JSON | native JSON ??, json.dumps? ??, ?? ? JSON ???/?? ?? ?? |
| BOOLEAN | MySQL TINYINT(1) ??, TRUE ??? ?? |
| TIMESTAMP | CURRENT_TIMESTAMP ??, updated_at? ???? ?? ??(?? ON UPDATE ??) |
| ALTER TABLE | 001/002? ? ?? ??, ?? ?? ??? ADD ??? ??, DDL ?? commit ?? |
| UNIQUE/INDEX | MySQL ?? ??, URL ASCII + UUID 2? ??? ?? 788???; InnoDB DYNAMIC ?? |
| FK/CASCADE | ?? PK? ??? charset/collation ?? ??, InnoDB?? ?? ?? ?? |
| UUID | VARCHAR(36) ??, provider ID? namespace UUID5? ?? |
| ?? | DECIMAL(10,8) ???DECIMAL(11,8) ?? ?? ??, provider ???? ?? ?? ?? |
| SQLite ?? | ???? DDL ??? MySQL ?? ??? ??. MySQL ?? upsert/row lock? ??? ??? ?? |

?? ?? ?? ??? ??? ?? ???? migration? ??. ?? 001/002? ????.
??? ENGINE/charset? DB??? ???? ????? ?? ??? ????.
001? NULL ???? ??? ?? hash? ???? ???. 002? ?? ??? reflection_rates? ????.

???? ?? ????? ??(????? ????? ??):

```powershell
mysql --default-character-set=utf8mb4 -h localhost -P 3306 -u root -p
```

?? DB??? ?? ??? ????. ?? DB ??? ??? tripclip? ???.

```sql
USE tripclip;
SELECT VERSION(), DATABASE(), @@default_storage_engine, @@innodb_default_row_format;
SHOW TABLES;
SHOW COLUMNS FROM users;
SHOW COLUMNS FROM trips;
SHOW COLUMNS FROM trip_members;
SHOW COLUMNS FROM user_preferences;
SHOW TABLE STATUS;
SHOW CREATE TABLE users;
SHOW CREATE TABLE trips;
SHOW CREATE TABLE shortform_contents;
SHOW COLUMNS FROM trip_itineraries;
SHOW COLUMNS FROM itinerary_places;
```

shortform_contents? ?? ??? ?? SHOW ??? 002 ??? ??? ? ??.
?? ? 001?? ?? ??? ??? ????. 002? ?? ???? ?? ???? ??? ????.
?? ?? ???? ??? ??? ??? ????. ?? ?? schema? DB?? ???? ???.

```sql
SOURCE backend/db/migrations/002_ai_persistence.sql;
```

001 ??? ??? ?? schema?? ?? `SOURCE backend/db/migrations/001_backend_schema_alignment.sql;`? ????.
owner ?? rename? 001? ??? ??? ?? ??? ???? ????.
FK ?? ?? collation? ?? DB ?? collation? ??? ?? ? ????? ??.
? ??? ??? DROP?? ?? migration? ???? ???.

?? ? DB? ?? ??? ???(?? ?? ?? DB? ??? ?? ?? ? ???? ?? DB ?? ??).

```sql
CREATE DATABASE tripclip CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tripclip;
SET SESSION default_storage_engine = InnoDB;
SOURCE backend/db/schema.sql;
SHOW TABLES;
```

MySQL 8 ?? innodb_default_row_format=DYNAMIC?? ????. ?? schema ?? ? 001/002? ?? ???? ???.

## ??? MySQL ?? ???

?? DB? ?? ????. ? DB ??? ??? ?? `_test`? ??? ??.
???? schema/migration? ???? ?? ?? ???? ??? UUID ?? ???????.
????? ???? ?? ?? DB? ??? DB? ???? ???. ???? ?? ?? ??? ? DB? ????.

```sql
CREATE DATABASE tripclip_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tripclip_test;
SET SESSION default_storage_engine = InnoDB;
SOURCE backend/db/schema.sql;
```

?? ??? DB_HOST/DB_PORT/DB_USER/DB_PASSWORD ????? ????.
DB_NAME? ? DB ???? ???? ??? DB? ?? ??? ???.

```powershell
$env:RUN_MYSQL_INTEGRATION_TESTS = "1"
$env:MYSQL_TEST_DB_NAME = "tripclip_test"
python -m unittest backend.tests.test_mysql_integration -v
$env:RUN_MYSQL_INTEGRATION_TESTS = "0"
```

?? ??? skip??. opt-in ? ??/schema? ???? skip? ?? ??? ????.
? ?????? ?? AI1/??? mock?? AI2 ??? ?? ??? ????. migration ?????/??? ??? ???.

`GET /health`? ?? ?? ??, `GET /health/db`? SELECT 1 ?? ????.
DB health? ?? 200 `{"status":"ok","database":"connected"}`, ?? 503?? ?????? ???? ???.

???? ??? ?? ??? `.env.example`? ????. `.env.example`? ???? ???? ?? ???? ???.
?? ??? API ?? ??? UUID ?? ??? [MANUAL_E2E.md](MANUAL_E2E.md)? ????.

??: [Kakao Local ?? ??](https://developers.kakao.com/docs/ko/local/dev-guide),
[MySQL JSON](https://dev.mysql.com/doc/refman/8.0/en/json.html),
[MySQL FK](https://dev.mysql.com/doc/refman/8.0/en/create-table-foreign-keys.html).
