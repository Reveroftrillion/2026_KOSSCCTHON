# Backend DB 정합성 및 실행 안내

```powershell
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
python -m unittest backend.tests.test_backend -v
```

Swagger: `http://localhost:8000/docs`. 현재 AI API 연결은 포함하지 않는다.
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

테스트는 스키마의 첫 4개 테이블을 SQLite 문법으로 조정하여 실제 HTTP와 SQL을 검증한다.
7개 필수 API, 소유자 필터, 삭제 cascade, bcrypt·72바이트 제한, 400/404/422, Swagger 계약을
포함한 10개 테스트가 통과했다. 실제 MySQL 엔진·마이그레이션 실행 검증을 대신하지 않는다.
