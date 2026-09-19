# 2026_KOSSCCTHON

## TripClip

> 숏폼 콘텐츠에서 발견한 장소와 활동을 저장하고, AI가 사용자별 취향을 분석하여 여러 사용자의 취향이 반영된 공동 일정 및 여행 코스를 생성하는 서비스

---

## 1. Problem

친구들과 여행이나 약속을 계획할 때 Instagram Reels, YouTube Shorts, TikTok 등에서 가고 싶은 장소를 발견해 서로 공유합니다.

하지만 실제 일정을 계획할 때는 다음과 같은 문제가 발생합니다.

- 가고 싶은 장소가 여러 SNS와 채팅방에 흩어져 있습니다.
- 이전에 공유한 숏폼 콘텐츠를 다시 찾기 어렵습니다.
- 구성원마다 원하는 장소와 취향이 다릅니다.
- 여러 사람의 의견을 비교하고 조율하는 과정이 필요합니다.
- 결국 특정 한 사람이 장소를 정리하고 일정을 계획하는 경우가 많습니다.

TripClip은 이러한 문제를 해결하기 위해 숏폼 콘텐츠를 단순히 저장하는 것에서 끝나지 않고, 각 사용자의 콘텐츠를 취향 데이터로 변환하여 공동 일정 생성에 활용합니다.

---

## 2. Solution

TripClip은 사용자가 공유하거나 저장한 숏폼 콘텐츠에서 AI를 이용해 장소와 활동 정보를 구조화합니다.

저장된 콘텐츠가 누적되면 사용자별 취향 DB를 생성하고, 여행이나 약속을 함께하는 구성원들의 취향을 분석합니다.

이후 다음 정보를 종합하여 공동 일정을 생성합니다.

- 각 사용자가 저장한 숏폼 콘텐츠
- AI가 분석한 장소 및 활동 정보
- 사용자별 취향
- 구성원들의 공통 관심사
- 여행 지역
- 날짜 및 시간
- 실제 장소 정보
- 추가 요청사항

단순히 장소를 모아주는 것이 아니라, 특정 한 사람의 취향에 치우치지 않도록 구성원들의 취향을 조율하는 것을 목표로 합니다.

---

## 3. Core Concept

기존의 숏폼 기반 여행 서비스가 콘텐츠에서 장소를 추출하고 일정을 정리하는 데 집중한다면, TripClip은 숏폼 콘텐츠를 사용자의 취향을 나타내는 데이터로 활용합니다.

```text
Short-form Content
        ↓
AI Content Analysis
        ↓
Place Verification
        ↓
Personal Preference DB
        ↓
Group Preference Analysis
        ↓
Preference Balancing
        ↓
AI Itinerary Generation
        ↓
Shared Schedule
```

핵심은 다음과 같습니다.

> 각자가 공유한 숏폼에서 취향을 분석하고, 여러 사람의 취향을 조율하여 모두가 만족할 수 있는 공동 경험을 만든다.

---

## 4. Key Features

### 4.1 숏폼 콘텐츠 저장

사용자는 SNS에서 발견한 콘텐츠를 TripClip에 저장할 수 있습니다.

서비스 확장 대상은 다음과 같습니다.

- Instagram Reels
- YouTube Shorts
- TikTok

현재 해커톤 MVP의 실제 분석 파이프라인은 YouTube Shorts를 중심으로 구현되어 있습니다.

사용자가 YouTube Shorts URL을 입력하면 영상 ID를 정규화한 뒤 YouTube oEmbed를 통해 공개 메타데이터를 수집합니다.

```text
YouTube Shorts URL
        ↓
Video ID 추출 및 URL 정규화
        ↓
YouTube oEmbed
        ↓
콘텐츠 메타데이터 수집
```

같은 사용자가 같은 여행방에 동일 영상을 다시 저장하는 경우 중복 콘텐츠로 판단합니다.

---

### 4.2 AI 콘텐츠 분석

숏폼 콘텐츠의 제목, 설명, 태그 등의 정보를 AI가 분석하여 일정 생성에 사용할 수 있는 데이터로 구조화합니다.

현재 Claude 기반 LLM 분석기를 사용하며, LLM 호출에 실패하거나 정상적인 구조화 결과를 얻을 수 없는 경우 기존 rule-based parser로 fallback할 수 있도록 구성했습니다.

추출 대상은 다음과 같습니다.

- 장소명
- 지역
- 카테고리
- 활동
- 키워드
- 추천 시간대

예시

```json
{
  "place_name": "이리에 라멘",
  "area": "합정",
  "category": "food",
  "keywords": [
    "food",
    "local",
    "ramen"
  ],
  "activity": "라멘 먹기",
  "recommended_time": null
}
```

현재 주요 카테고리는 다음과 같습니다.

```text
cafe
food
exhibition
shopping
outdoor
activity
sightseeing
nightlife
accommodation
other
```

AI가 정확하게 판단하기 어려운 정보는 사용자가 확인하거나 수정할 수 있도록 구성합니다.

---

### 4.3 단일 장소와 모음형 콘텐츠 구분

TripClip은 숏폼의 전체 제목을 무조건 장소명으로 저장하지 않습니다.

예를 들어 다음과 같은 콘텐츠는 여러 장소를 소개하는 모음형 콘텐츠로 처리합니다.

```text
성수동 맛집 TOP 10
연남동 디저트 5곳
홍대 맛집 BEST 8
```

이 경우 분석 결과는 다음과 같은 형태가 됩니다.

```json
{
  "area": "성수동",
  "category": "food",
  "place_name": null
}
```

반대로 하나의 특정 장소를 소개하는 콘텐츠는 실제 장소명을 추출합니다.

```text
이게 진짜 라멘이지!! 합정 맛집 이리에 라멘
```

```json
{
  "area": "합정",
  "category": "food",
  "place_name": "이리에 라멘"
}
```

이를 통해 추천 목록이나 지역 전체가 하나의 실제 장소처럼 저장되는 문제를 줄였습니다.

---

### 4.4 Kakao Place Verification

AI가 특정 단일 장소명을 추출한 경우 Kakao Local API를 사용해 실제 장소인지 검증합니다.

```text
AI Place Name
        ↓
Kakao Local Search
        ↓
Place Name Normalization
        ↓
실제 장소 확인
        ↓
주소 / 좌표 저장
```

예를 들어 AI가 다음 장소명을 추출할 수 있습니다.

```text
이리에 라멘
```

Kakao에는 다음과 같이 등록되어 있습니다.

```text
이리에라멘
```

TripClip은 공백과 일부 구두점을 제거해 동일한 장소인지 비교합니다.

또한 지점명 차이도 일부 정규화합니다.

```text
AI
담택

Kakao
담택 본점

→ 본점 suffix 제거 후 동일 장소로 검증
```

검증이 성공하면 다음 정보를 저장합니다.

```json
{
  "place_name": "담택 본점",
  "address": "서울 마포구 동교로12안길 51",
  "latitude": 37.5544519994,
  "longitude": 126.9151652547
}
```

Kakao 장소 검증에 실패하더라도 숏폼 콘텐츠 자체는 저장할 수 있습니다.

이 경우 해당 콘텐츠는 미검증 장소로 유지됩니다.

---

### 4.5 AI 분석 결과 확인 및 수정

사용자는 AI가 분석한 결과를 Frontend에서 확인할 수 있습니다.

현재 확인 가능한 정보는 다음과 같습니다.

- 장소 확인 여부
- 주소
- 지역
- 활동 유형
- 장소명
- 카테고리
- 추천 시간대
- 키워드

장소 상태는 다음과 같이 구분합니다.

```text
단일 장소 + Kakao 검증 성공
→ 카카오맵에서 실제 장소를 확인했습니다.

장소명 추출 + Kakao 검증 실패
→ 장소명을 추출했지만 카카오맵에서 정확히 확인하지 못했습니다.

단일 장소 없음
→ 여러 장소를 소개하는 콘텐츠이거나 특정 장소가 확인되지 않았습니다.
```

사용자가 분석 결과를 수정한 뒤 저장하면 PATCH API를 통해 DB에 반영됩니다.

장소명을 수정한 경우 Kakao Local API를 통해 다시 장소 검증을 수행합니다.

```text
AI 분석
        ↓
사용자 확인
        ↓
장소명 / 카테고리 / 태그 수정
        ↓
PATCH
        ↓
DB 업데이트
        ↓
취향 DB 재계산
```

---

### 4.6 Shared Trip Basket

그룹 구성원들이 저장한 콘텐츠를 하나의 공동 공간에서 확인할 수 있습니다.

예시

```text
원영
- 이리에라멘
- 성수 맛집 TOP 10
- 담택 본점

민수
- 서울숲
- 전시회

지수
- 디저트 카페
- 쇼핑 스팟
```

장바구니에서는 저장한 사용자와 카테고리를 기준으로 콘텐츠를 확인할 수 있습니다.

이를 통해 SNS나 채팅방에 흩어져 있던 여행 및 약속 정보를 하나의 공간에서 관리합니다.

---

### 4.7 Personal Preference DB

사용자가 저장한 콘텐츠를 기반으로 개인별 취향 정보를 누적합니다.

예시

```text
원영

Food        0.60
Cafe        0.20
Exhibition  0.20

Keywords

local       0.60
ramen       0.40
date        0.20
```

사용자가 특정 카테고리 또는 키워드의 콘텐츠를 반복적으로 저장할수록 해당 취향의 비중이 높아집니다.

취향 DB는 사용자가 직접 작성하는 프로필이 아니라 실제 저장 행동을 기반으로 생성됩니다.

콘텐츠가 추가, 수정 또는 삭제되면 해당 사용자의 전체 저장 이력을 기준으로 취향을 다시 계산합니다.

---

### 4.8 Group Preference Analysis

여행방에 참여한 사용자들의 취향 DB를 비교하여 그룹의 공통 관심사와 개인별 특성을 분석합니다.

예시

```text
원영
Food / Ramen / Local

민수
Shopping / Activity

지수
Exhibition / Cafe / Photo
```

그룹 취향 화면에서는 멤버별 취향을 상대 점수로 정규화해 비교할 수 있습니다.

```text
각 사용자의 가장 높은 취향 = 100
```

이를 기반으로 다음 정보를 확인할 수 있습니다.

- 여러 구성원이 공통적으로 강하게 선호하는 항목
- 특정 사용자에게 특히 강한 개인 취향
- 구성원 간 취향 차이
- 일정 생성 시 고려해야 할 취향 분포

---

### 4.9 AI Itinerary Planner

그룹의 취향 데이터와 실제 장소 후보를 기반으로 AI가 공동 일정을 생성합니다.

입력 정보 예시

```text
지역: 성수

날짜:
2026-09-20

시간:
13:00 ~ 20:00

참여자:
원영 / 민수 / 지수

조건:
사용자 추가 요청
```

일정 생성 시 다음 데이터를 사용합니다.

```text
여행 정보
+
현재 여행 멤버
+
각 멤버의 Preference Profile
+
Kakao Local 장소 후보
+
사용자 조건
```

장소마다 사용자별 취향 점수와 그룹 점수를 계산합니다.

예시

```json
{
  "place": "이리에라멘",
  "category": "food",
  "user_scores": {
    "user-a": 1.0,
    "user-b": 0.2,
    "user-c": 0.0
  },
  "group_score": 0.4
}
```

---

### 4.10 Preference Balance

TripClip의 핵심 차별점 중 하나입니다.

AI가 일정을 생성할 때 단순히 평균 점수가 가장 높은 장소만 반복적으로 선택하면 특정 사용자의 취향만 일정에 반영될 수 있습니다.

이를 줄이기 위해 이미 충분히 반영된 사용자보다 아직 취향이 적게 반영된 사용자의 후보를 일정에 포함할 수 있도록 fairness logic을 적용했습니다.

예시

```text
취향 반영도

원영 100%
민수 100%
지수 100%
```

반영도는 AI가 임의의 문장으로 생성하는 값이 아니라 사용자의 실제 preference와 일정에 선택된 카테고리를 기반으로 계산합니다.

---

## 5. Service Flow

```text
1. 사용자 생성
        ↓
2. 여행 그룹 생성
        ↓
3. 여행 멤버 추가
        ↓
4. 각자 YouTube Shorts URL 저장
        ↓
5. YouTube 메타데이터 수집
        ↓
6. Claude 콘텐츠 분석
        ↓
7. 장소 / 카테고리 / 키워드 구조화
        ↓
8. Kakao 실제 장소 검증
        ↓
9. 개인 취향 DB 업데이트
        ↓
10. AI 분석 결과 사용자 확인 및 수정
        ↓
11. 그룹 취향 분석
        ↓
12. 날짜 / 시간 / 지역 입력
        ↓
13. AI 공동 일정 생성
        ↓
14. 사용자별 취향 반영 근거 표시
```

---

## 6. AI Pipeline

TripClip에서는 AI 기능을 크게 두 단계로 나눕니다.

### AI 1. Content & Preference Analyzer

역할

```text
YouTube Shorts
        ↓
메타데이터 수집
        ↓
Claude 분석
        ↓
장소 / 지역 / 카테고리 / 키워드 추출
        ↓
Kakao 장소 검증
        ↓
사용자 취향 DB 업데이트
```

입력 예시

```json
{
  "title": "이게 진짜 라멘이지!! 합정 맛집 이리에 라멘",
  "description": "",
  "tags": [
    "라멘",
    "일식",
    "합정맛집"
  ]
}
```

출력 예시

```json
{
  "place_name": "이리에 라멘",
  "area": "합정",
  "category": "food",
  "keywords": [
    "food",
    "local",
    "ramen"
  ],
  "activity": "라멘 먹기",
  "recommended_time": null
}
```

LLM 응답은 Pydantic schema를 통해 검증합니다.

LLM 호출 또는 결과 검증에 실패할 경우 rule-based analyzer로 fallback할 수 있도록 구성했습니다.

---

### AI 2. Group Itinerary Planner

역할

```text
개인 취향 DB
+
그룹 멤버
+
Kakao 장소 후보
+
날짜 / 시간 / 지역
+
사용자 조건
        ↓
그룹 취향 분석
        ↓
사용자별 장소 점수 계산
        ↓
취향 균형 보정
        ↓
공동 일정 생성
```

출력 예시

```json
{
  "summary": "성수 지역 일정으로 4개 장소를 구성했습니다.",
  "schedule": [
    {
      "time": "13:00",
      "place": "대성갈비",
      "category": "food",
      "group_score": 0.4,
      "related_users": [
        "user-uuid"
      ],
      "reason": "해당 사용자의 food 취향을 반영한 장소입니다."
    }
  ]
}
```

---

## 7. MVP

해커톤에서는 다음 흐름의 완성을 최우선 목표로 합니다.

```text
숏폼 URL 입력
        ↓
AI 콘텐츠 정보 추출
        ↓
실제 장소 검증
        ↓
그룹 저장
        ↓
개인 취향 데이터 생성
        ↓
그룹 취향 분석
        ↓
AI 공동 일정 생성
        ↓
추천 이유 및 취향 반영도 표시
```

### Must Have

- 그룹 생성
- 사용자별 숏폼 URL 등록
- AI 콘텐츠 구조화
- Kakao 실제 장소 검증
- 콘텐츠 공동 보관함
- AI 분석 결과 확인 및 수정
- 개인 취향 분석
- 그룹 취향 분석
- 공동 일정 생성
- 일정 생성 근거 표시

### Nice to Have

- 지도 기반 일정 표시
- 장소 간 실제 이동거리 계산
- 취향 분석 시각화 개선
- 일정 재생성 및 수정 요청
- Instagram Reels 및 TikTok 실제 연동
- 숏폼 공유 기능 연동

### MVP 제외

- 완전한 SNS 로그인
- 모든 SNS 공식 API 연동
- 숏폼 영상 다운로드
- 영상 전체 멀티모달 분석
- 자체 AI 모델 학습
- 실시간 채팅
- 친구 및 팔로우 시스템

---

## 8. System Architecture

```text
┌─────────────────────────────────────┐
│              Frontend               │
│                                     │
│ Next.js / React / TypeScript        │
│ 그룹 / 숏폼 / 취향 / 일정 UI        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│              Backend                │
│                                     │
│ FastAPI / SQLAlchemy                │
│ User / Trip / Member / Content API  │
└──────────┬──────────────┬───────────┘
           │              │
           ▼              ▼
┌─────────────────┐  ┌─────────────────┐
│      AI 1       │  │      AI 2       │
│                 │  │                 │
│ Content &       │  │ Group Preference│
│ Preference      │  │ & Itinerary     │
│ Analyzer        │  │ Planner         │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────────────────────────┐
│               MySQL                 │
│                                     │
│ User / Trip / Content / Preference  │
│ Place / Itinerary                   │
└─────────────────┬───────────────────┘
                  │
                  ▼
          ┌──────────────────┐
          │   Kakao Local    │
          │ Place Validation │
          └──────────────────┘
```

---

## 9. Team

| Role | Member | Responsibility |
|---|---|---|
| Frontend |  | 그룹 생성 및 숏폼 입력 UI |
| Frontend |  | 공동 보관함, 그룹 취향 및 일정 UI |
| Backend |  | API, DB, 그룹 및 콘텐츠 관리 |
| AI |  | 숏폼 콘텐츠 분석 및 취향 DB |
| AI |  | 그룹 취향 분석 및 일정 생성 |

---

## 10. Repository Structure

```text
2026_KOSSCCTHON/
│
├── ai/
│   ├── preference_analyzer/
│   │   ├── content_parser.py
│   │   ├── llm_parser.py
│   │   ├── rule_parser.py
│   │   ├── schemas.py
│   │   └── metadata_fetcher.py
│   │
│   └── itinerary_planner/
│       ├── group_preference.py
│       ├── itinerary.py
│       ├── place_selector.py
│       └── sample_places.json
│
├── backend/
│   ├── db/
│   │   ├── schema.sql
│   │   └── migrations/
│   │
│   ├── routers/
│   │   ├── members.py
│   │   ├── shortforms.py
│   │   ├── preferences.py
│   │   └── itineraries.py
│   │
│   ├── services/
│   │   ├── common.py
│   │   ├── preference_service.py
│   │   ├── place_service.py
│   │   └── itinerary_service.py
│   │
│   ├── tests/
│   ├── database.py
│   └── main.py
│
├── web/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── public/
│   ├── package.json
│   └── pnpm-lock.yaml
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 11. Development Roles

### Frontend 1

- 메인 화면
- 그룹 생성
- 그룹 참가
- 숏폼 URL 입력
- AI 분석 결과 확인 및 수정

### Frontend 2

- Shared Trip Basket
- 사용자별 저장 장소 표시
- 그룹 취향 비교
- 여행 조건 입력
- 공동 일정 결과
- 취향 반영 근거 UI
- Kakao Map 표시

### Backend

- 사용자 관리
- 여행 그룹 관리
- 멤버 관리
- 콘텐츠 저장 및 수정 API
- AI API 연결
- Kakao Local API 연결
- 취향 DB 관리
- 일정 생성 및 영속화 API

### AI 1

- YouTube 숏폼 메타데이터 구조화
- 장소 및 카테고리 추출
- 키워드 추출
- 모음형 콘텐츠 구분
- 사용자 취향 점수 계산 및 업데이트

### AI 2

- 개인별 취향 DB 분석
- 그룹 취향 분석
- 구성원 간 취향 조율
- 장소 후보 평가
- 일정 생성
- 추천 이유 생성
- 취향 반영도 계산

---

## 12. Tech Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- TanStack React Query
- React Hook Form
- Zod
- shadcn
- Lucide React
- react-kakao-maps-sdk
- pnpm

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- PyMySQL
- Pydantic
- HTTPX
- bcrypt

### AI

- Claude Sonnet via OpenAI-compatible API
- Rule-based parser fallback
- Custom Preference Analyzer
- Group Preference Analysis
- Preference-aware Itinerary Planner

### Database

- MySQL 8
- InnoDB
- utf8mb4
- JSON columns
- UUID 기반 내부 ID

### External API

- YouTube oEmbed
- 국민대학교 OpenAI-compatible Claude API
- Kakao Local API
- Kakao Maps JavaScript API

### Deployment

현재 개발 및 Full-stack 통합 테스트 단계입니다.

---

## 13. Database Structure

현재 주요 테이블은 다음과 같습니다.

```text
users
user_preferences
trips
trip_members
shortform_contents
places
saved_places
trip_itineraries
itinerary_places
```

AI가 추출한 단일 장소가 Kakao에서 검증되면 `shortform_contents.place_id`를 통해 실제 장소 테이블과 연결합니다.

```text
shortform_contents
        │
        │ place_id
        ▼
places
├── place_name
├── category
├── address
├── latitude
└── longitude
```

Kakao의 provider ID는 그대로 DB PK로 사용하지 않고 namespace 기반 UUID5로 변환하여 TripClip 내부 `place_id`로 사용합니다.

---

## 14. API

### User

```text
POST   /api/users
GET    /api/users
GET    /api/users/{user_id}
GET    /api/users/{user_id}/trips
```

### Trip

```text
POST   /api/trips
GET    /api/trips/{trip_id}
PUT    /api/trips/{trip_id}
DELETE /api/trips/{trip_id}
```

### Member

```text
POST   /api/trips/{trip_id}/members
GET    /api/trips/{trip_id}/members
DELETE /api/trips/{trip_id}/members/{user_id}
```

### Shortform

```text
POST   /api/trips/{trip_id}/shortforms
GET    /api/trips/{trip_id}/shortforms
PATCH  /api/trips/{trip_id}/shortforms/{content_id}
DELETE /api/trips/{trip_id}/shortforms/{content_id}
```

### Preference

```text
GET /api/users/{user_id}/preferences
GET /api/trips/{trip_id}/preferences
```

### Itinerary

```text
POST /api/trips/{trip_id}/itinerary
GET  /api/trips/{trip_id}/itineraries
GET  /api/trips/{trip_id}/itineraries/{itinerary_id}
```

Swagger 문서는 Backend 실행 후 다음 주소에서 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

---

## 15. Environment Variables

### Backend

루트 `.env.example`을 참고합니다.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=tripclip_dev

LLM_API_KEY=
LLM_BASE_URL=https://ai.cs.kookmin.ac.kr/v1
LLM_MODEL=claude-sonnet-4-5

YOUTUBE_API_KEY=

KAKAO_REST_API_KEY=

RUN_MYSQL_INTEGRATION_TESTS=0
MYSQL_TEST_DB_NAME=tripclip_test
```

현재 Backend는 `.env` 파일을 자동으로 로드하지 않으므로 개발 시 실행 터미널에 환경변수를 설정합니다.

Windows CMD 예시

```cmd
set "DB_HOST=localhost"
set "DB_PORT=3306"
set "DB_USER=root"
set "DB_PASSWORD=YOUR_PASSWORD"
set "DB_NAME=tripclip_dev"

set "LLM_API_KEY=YOUR_LLM_API_KEY"
set "LLM_BASE_URL=https://ai.cs.kookmin.ac.kr/v1"
set "LLM_MODEL=claude-sonnet-4-5"

set "KAKAO_REST_API_KEY=YOUR_KAKAO_REST_API_KEY"
```

### Frontend

`web/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_KAKAO_MAP_KEY=YOUR_KAKAO_JAVASCRIPT_KEY
```

Kakao REST API Key와 JavaScript Key는 용도가 다릅니다.

```text
Backend
KAKAO_REST_API_KEY
→ Kakao Local REST API

Frontend
NEXT_PUBLIC_KAKAO_MAP_KEY
→ Kakao Maps JavaScript SDK
```

실제 API Key와 DB 비밀번호는 Git에 commit하지 않습니다.

---

## 16. Run

### Backend

프로젝트 루트에서 실행합니다.

```cmd
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app
```

Backend

```text
http://127.0.0.1:8000
```

Swagger

```text
http://127.0.0.1:8000/docs
```

DB Health

```text
http://127.0.0.1:8000/health/db
```

정상 응답

```json
{
  "status": "ok",
  "database": "connected"
}
```

### Frontend

```cmd
cd web
pnpm install
pnpm dev
```

Frontend

```text
http://localhost:3000
```

---

## 17. Database Setup

MySQL 8 이상을 권장합니다.

개발 DB 예시

```sql
CREATE DATABASE tripclip_dev
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

테스트 DB 예시

```sql
CREATE DATABASE tripclip_test
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

신규 DB에는 최신 schema를 적용합니다.

```sql
USE tripclip_dev;

SOURCE C:/path/to/2026_KOSSCCTHON/backend/db/schema.sql;
```

기존 DB에는 필요한 migration을 순서대로 적용합니다.

```text
backend/db/migrations/
├── 001_backend_schema_alignment.sql
├── 002_ai_persistence.sql
└── 003_shortform_place_verification.sql
```

`003_shortform_place_verification.sql`은 `shortform_contents.place_id`와 `places` 테이블 사이의 FK 연결을 추가합니다.

---

## 18. Verification

### Backend Test

```cmd
python -m unittest discover -s backend/tests -t . -v
```

현재 통합 작업 기준 결과

```text
Ran 52 tests

OK (skipped=1)
```

Backend 테스트에서는 사용자, 여행, 멤버, 숏폼, 취향, 일정 생성 및 저장 흐름을 검증합니다.

### Frontend Lint

```cmd
cd web
pnpm exec eslint src
```

현재 결과

```text
0 errors
2 warnings
```

현재 warning은 React Hook Form의 `watch()`와 React Compiler memoization 관련 경고이며 기능 오류는 확인되지 않았습니다.

---

## 19. Current Full-stack Integration Status

현재까지 실제 Frontend와 Backend를 함께 실행하여 다음 흐름을 확인했습니다.

```text
Frontend
        ↓
FastAPI
        ↓
YouTube oEmbed
        ↓
Claude
        ↓
Content Parser
        ↓
Kakao Local
        ↓
MySQL
        ↓
Frontend Review
        ↓
사용자 수정
        ↓
PATCH
        ↓
Preference Recalculation
```

확인된 주요 기능은 다음과 같습니다.

- 실제 Backend 사용자 목록 조회
- 여행방 생성
- 여행 멤버 연결
- YouTube Shorts 입력
- Claude 분석
- 모음형 콘텐츠와 단일 장소 콘텐츠 구분
- Kakao 실제 장소 검색
- 장소 주소 및 좌표 저장
- `shortform_contents.place_id`와 `places` 연결
- Frontend에서 실제 장소 확인 상태 표시
- AI 분석 결과 사용자 수정
- PATCH API를 통한 수정 결과 저장
- 수정 후 사용자 취향 재계산
- Backend 전체 테스트 통과

실제 검증 예시

```text
AI 장소명
이리에 라멘

Kakao 장소명
이리에라멘

주소
서울 마포구 성지1길 18

결과
실제 장소 확인 성공
```

또 다른 예시

```text
AI 장소명
담택

Kakao 장소명
담택 본점

결과
지점 suffix 정규화 후 실제 장소 확인 성공
```

---

## 20. Remaining Work

현재 Shortform 분석 및 장소 검증 Full-stack 흐름은 연결된 상태입니다.

다음 통합 우선순위는 다음과 같습니다.

```text
Shared Trip Basket 최종 검증
        ↓
Group Preference Frontend ↔ Backend 연결
        ↓
Itinerary Frontend ↔ Backend 연결
        ↓
실제 Kakao 장소 후보 기반 일정 생성
        ↓
Kakao Map 일정 표시
        ↓
전체 End-to-End 테스트
        ↓
배포 준비
```

---

## 21. Difference

TripClip은 숏폼 콘텐츠에서 장소를 추출하여 여행 일정을 만드는 것만을 목표로 하지 않습니다.

숏폼 콘텐츠를 각 사용자의 취향을 나타내는 데이터로 해석하고, 여러 사용자의 취향을 분석 및 조율하여 공동 일정에 반영합니다.

```text
기존 접근

숏폼
→ 장소 추출
→ 장소 저장
→ 여행 일정
```

```text
TripClip

숏폼
→ 장소 및 취향 추출
→ 실제 장소 검증
→ 개인 취향 DB
→ 그룹 취향 분석
→ 취향 조율
→ 공동 일정
```

핵심 차별점은 다음과 같습니다.

> 장소를 정리하는 것이 아니라 사람들의 취향을 조율한다.

---

## 22. Goal

TripClip의 최종 목표는 사용자가 직접 여행 취향을 일일이 입력하지 않아도, 평소 저장하고 공유하는 콘텐츠를 통해 자연스럽게 취향을 파악하는 것입니다.

그리고 여러 사람이 함께 계획을 세울 때 각자의 취향과 관심사를 AI가 분석하여 특정 한 사람에게 계획 부담이 집중되지 않도록 지원합니다.

> Save what you like.  
> Share what you want.  
> Plan together.

---

## Itinerary Frontend ↔ Backend 확인

실제 모드(`NEXT_PUBLIC_USE_MOCK=false`)의 일정 화면은 다음 API를 사용합니다.

- 생성: `POST /api/trips/{trip_id}/itinerary`, 본문 `{"date":"2026-09-20","user_conditions":[]}`
- 복원: `GET /api/trips/{trip_id}/itineraries` 후 선택 일정의 `/{itinerary_id}` 조회
- 현재 단일 날짜 결과 화면은 재진입 시 저장된 일정 중 마지막 여행 날짜를 표시합니다.

날짜는 여행 기간 내에서 선택하고 지역·시작/종료 시간은 여행방 DB 설정을 사용합니다.
예산·식사·필수 장소 조건은 아직 보장되지 않아 실제 모드 입력에서 숨깁니다.
일정은 저장한 장소의 단순 나열이 아니라 그룹 취향으로 검색한 후보에서 생성됩니다.
지도 연결선은 방문 순서이며 실제 도로 경로나 이동 시간 보장을 의미하지 않습니다.

API adapter는 ID, 추천 이유, 사용자/그룹 점수, coverage/reflection을 보존합니다.
반영률은 Backend 값을 표시하며 빈 취향의 null 값은 '취향 데이터 없음'으로 표시합니다.
신규 일정은 좌표·주소를 snapshot에 저장하고, 이전 일정의 누락된 위치 필드는 places에서 보완합니다.
DB schema/migration 변경은 없습니다. Backend가 mock 장소를 반환하면 실제 모드에서는 샘플을 표시하지 않고 설정 확인 오류를 보여줍니다.

브라우저 수동 확인:

1. Backend와 Frontend를 실행하고 Frontend의 실제 모드 및 API 주소 설정을 확인합니다.
2. Backend에는 Kakao REST 키, Frontend에는 `NEXT_PUBLIC_KAKAO_MAP_KEY`를 환경변수로 설정합니다. 환경변수 변경 후 서버를 재시작합니다.
3. 숏폼과 멤버가 있는 여행방에서 일정 화면을 열고 날짜를 선택해 생성합니다.
4. Network에서 POST 경로/본문과 201 응답을 확인합니다.
5. 방문 시간·장소·주소·카테고리·추천 이유·사용자별 반영률을 확인합니다.
6. 지도 마커를 눌러 해당 일정 카드가 선택되는지 확인합니다. 좌표나 지도 키가 없으면 목록은 유지됩니다.
7. 새로고침 후 목록/상세 GET으로 일정이 복원되는지 확인합니다. 같은 날짜 재생성은 해당 날짜만 대체합니다.
8. 기존 Shorts Review 수정·저장, Shared Basket, Group Preference도 확인합니다.

회귀 테스트(프로젝트 루트 기준):

```powershell
python -m unittest discover -s backend/tests -t . -v
cd web
pnpm exec eslint src
pnpm exec tsc --noEmit
node tests/itinerary-contract.test.cjs
```

## Contributors

2026 KOSSCCTHON Team 7 (111)
