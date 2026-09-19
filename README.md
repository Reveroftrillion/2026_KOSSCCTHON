# 2026_KOSSCCTHON

## TripClip

> 숏폼 콘텐츠에서 발견한 장소와 활동을 저장하고, AI가 사용자별 취향을 분석하여 여러 사용자의 취향이 반영된 공동 여행 일정을 생성하는 서비스

---

## 1. Problem

친구들과 여행이나 약속을 계획할 때 YouTube Shorts, Instagram Reels, TikTok 등에서 가고 싶은 장소를 발견해 서로 공유합니다.

하지만 실제 일정을 계획하려고 하면 다음과 같은 문제가 발생합니다.

- 가고 싶은 장소가 여러 SNS와 채팅방에 흩어져 있습니다.
- 이전에 공유한 숏폼 콘텐츠를 다시 찾기 어렵습니다.
- 구성원마다 선호하는 장소와 활동이 다릅니다.
- 여러 사람의 의견을 직접 비교하고 조율해야 합니다.
- 결국 특정 한 사람이 장소를 정리하고 일정을 만드는 경우가 많습니다.

TripClip은 숏폼 콘텐츠를 단순히 저장하는 것에서 끝나지 않고, 각 사용자가 저장한 콘텐츠를 취향 데이터로 변환하여 공동 일정 생성에 활용합니다.

---

## 2. Solution

TripClip은 사용자가 저장한 숏폼 콘텐츠의 제목, 설명, 태그 등의 정보를 AI로 분석하여 여행 계획에 사용할 수 있는 구조화된 데이터로 변환합니다.

저장된 콘텐츠가 누적되면 사용자별 취향 DB를 생성하고, 여행방 구성원들의 취향을 비교하여 공동 일정을 생성합니다.

일정 생성에는 다음 정보가 사용됩니다.

- 사용자가 저장한 숏폼 콘텐츠
- AI가 분석한 장소 및 활동 정보
- 사용자별 카테고리 및 키워드 취향
- 여행방 구성원들의 취향 분포
- 여행 지역
- 날짜 및 시간
- Kakao에서 검증한 실제 장소 정보

TripClip의 목표는 단순히 인기 장소를 추천하는 것이 아니라, 특정 한 사람에게 일정이 편향되지 않도록 여러 사용자의 취향을 함께 반영하는 것입니다.

---

## 3. Core Concept

기존 숏폼 기반 여행 서비스가 콘텐츠에서 장소를 추출하고 저장하는 데 집중한다면, TripClip은 숏폼 콘텐츠를 사용자의 취향을 나타내는 데이터로 활용합니다.

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

> 각자가 저장한 숏폼에서 취향을 분석하고, 여러 사람의 취향을 조율하여 모두가 함께 사용할 수 있는 일정을 만든다.

---

## 4. Key Features

### 4.1 숏폼 콘텐츠 저장

사용자는 SNS에서 발견한 숏폼 콘텐츠를 여행방에 저장할 수 있습니다.

서비스 확장 대상은 다음과 같습니다.

- YouTube Shorts
- Instagram Reels
- TikTok

현재 해커톤 MVP의 실제 분석 파이프라인은 YouTube Shorts를 중심으로 구현되어 있습니다.

```text
YouTube Shorts URL
        ↓
Video ID 추출 및 URL 정규화
        ↓
YouTube oEmbed
        ↓
공개 메타데이터 수집
        ↓
AI 분석
```

같은 사용자가 같은 여행방에 동일 영상을 다시 저장하는 경우 중복 콘텐츠로 처리합니다.

---

### 4.2 AI 콘텐츠 분석

숏폼의 제목, 설명, 태그를 AI가 분석하여 일정 생성에 사용할 수 있는 데이터로 구조화합니다.

추출 정보는 다음과 같습니다.

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

LLM 응답은 Pydantic schema를 통해 검증하며, 정상적인 구조화 결과를 얻지 못하는 경우 rule-based parser로 fallback할 수 있도록 구성했습니다.

---

### 4.3 단일 장소와 모음형 콘텐츠 구분

TripClip은 숏폼 제목 전체를 무조건 장소명으로 사용하지 않습니다.

예를 들어 다음 콘텐츠는 여러 장소를 소개하는 모음형 콘텐츠입니다.

```text
성수동 맛집 TOP 10
연남동 디저트 5곳
홍대 맛집 BEST 8
```

이런 경우 특정 장소는 추출하지 않습니다.

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

AI가 특정 단일 장소명을 추출한 경우 Kakao Local API를 이용해 실제 장소인지 검증합니다.

```text
AI Place Name
        ↓
Kakao Local Search
        ↓
Place Name Normalization
        ↓
실제 장소 검증
        ↓
주소 및 좌표 저장
```

예를 들어 AI 결과와 Kakao의 표기가 조금 다른 경우에도 장소명 정규화를 통해 동일 장소인지 확인합니다.

```text
AI
이리에 라멘

Kakao
이리에라멘

→ 동일 장소로 검증
```

지점명이 추가된 경우에도 일부 suffix를 고려합니다.

```text
AI
담택

Kakao
담택 본점

→ 동일 장소로 검증
```

검증에 성공하면 다음 정보를 저장합니다.

```json
{
  "place_name": "담택 본점",
  "address": "서울 마포구 동교로12안길 51",
  "latitude": 37.5544519994,
  "longitude": 126.9151652547
}
```

Kakao에서 정확한 장소를 찾지 못해도 숏폼 자체는 저장할 수 있으며, 해당 콘텐츠는 미검증 상태로 유지됩니다.

---

### 4.5 AI 분석 결과 확인 및 수정

사용자는 AI 분석 결과를 저장하기 전에 확인하고 수정할 수 있습니다.

확인 가능한 정보는 다음과 같습니다.

- 실제 장소 검증 여부
- 장소명
- 주소
- 지역
- 활동 유형
- 카테고리
- 추천 시간대
- 키워드

장소 상태는 다음과 같이 구분합니다.

```text
단일 장소 + Kakao 검증 성공
→ 카카오맵에서 실제 장소를 확인했습니다.

장소명 추출 + Kakao 검증 실패
→ 장소명을 추출했지만 카카오맵에서 정확히 확인하지 못했습니다.

특정 장소 없음
→ 여러 장소를 소개하는 콘텐츠이거나 특정 장소가 확인되지 않았습니다.
```

사용자가 수정한 결과는 PATCH API를 통해 DB에 반영됩니다.

```text
AI 분석
        ↓
사용자 확인
        ↓
장소명 / 카테고리 / 키워드 수정
        ↓
PATCH
        ↓
DB 업데이트
        ↓
Preference 재계산
```

장소명을 수정한 경우 Kakao Local API를 통해 다시 검증합니다.

---

### 4.6 Shared Trip Basket

여행방 구성원들이 저장한 콘텐츠를 하나의 공동 공간에서 확인할 수 있습니다.

```text
원영
- 이리에라멘
- 담택 본점
- 성수 맛집 TOP 10

민수
- 서울숲
- 전시회

지수
- 디저트 카페
- 쇼핑 스팟
```

각 콘텐츠에는 저장한 사용자, 카테고리, 지역, 키워드 등의 정보가 함께 표시됩니다.

이를 통해 SNS나 채팅방에 흩어져 있던 여행 정보를 하나의 여행방에서 관리할 수 있습니다.

---

### 4.7 Personal Preference DB

사용자가 저장한 콘텐츠를 기반으로 개인별 취향 정보를 누적합니다.

예시

```text
원영

Category

Food         0.60
Cafe         0.20
Exhibition   0.20

Keyword

local        0.60
ramen        0.40
date         0.20
```

특정 카테고리 또는 키워드의 콘텐츠를 반복적으로 저장할수록 해당 취향의 비중이 높아집니다.

취향 DB는 사용자가 직접 설문으로 작성하는 프로필이 아니라 실제 콘텐츠 저장 행동을 기반으로 생성됩니다.

콘텐츠가 추가, 수정 또는 삭제되면 해당 사용자의 저장 이력을 기준으로 취향을 다시 계산합니다.

---

### 4.8 Group Preference Analysis

여행방에 참여한 사용자들의 Preference DB를 비교하여 그룹의 공통 관심사와 개인별 특성을 분석합니다.

예시

```text
원영
Food / Ramen / Local

민수
Shopping / Activity

지수
Exhibition / Cafe / Photo
```

그룹 취향 화면에서는 각 사용자의 취향을 상대 점수로 정규화하여 비교할 수 있습니다.

```text
각 사용자의 가장 높은 취향 = 100
```

이를 통해 다음 정보를 확인할 수 있습니다.

- 여러 구성원이 공통적으로 선호하는 카테고리
- 특정 사용자에게 강하게 나타나는 개인 취향
- 구성원 간 취향 차이
- 일정 생성 시 고려해야 할 취향 분포

---

### 4.9 AI Itinerary Planner

그룹의 취향 데이터와 Kakao의 실제 장소 후보를 기반으로 공동 일정을 생성합니다.

입력 예시

```text
지역: 성수

날짜:
2026-09-20

시간:
13:00 ~ 20:00

참여자:
원영 / 민수 / 지수
```

일정 생성에는 다음 데이터가 사용됩니다.

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

```json
{
  "place": "대성갈비",
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

TripClip의 핵심 기능 중 하나입니다.

단순히 평균 점수가 높은 장소만 선택하면 특정 사용자의 취향만 반복적으로 일정에 반영될 수 있습니다.

이를 줄이기 위해 이미 충분히 반영된 사용자보다 아직 취향이 적게 반영된 사용자의 후보를 일정에 포함할 수 있도록 fairness logic을 적용합니다.

실제 테스트에서는 다음과 같이 완전히 다른 취향을 가진 세 사용자를 구성했습니다.

```text
사용자 A
food

사용자 B
sightseeing

사용자 C
exhibition
```

생성 결과

```text
서울숲 곤충식물원
→ sightseeing
→ 관광 취향 사용자 반영

언더스탠드에비뉴 아트스탠드
→ exhibition
→ 전시 취향 사용자 반영

대성갈비
→ food
→ 음식 취향 사용자 반영
```

세 사용자의 선호 카테고리가 모두 일정에 포함되어 각각 100%의 취향 반영도를 확인했습니다.

---

### 4.11 Preference Reflection

일정 생성 이후 각 사용자의 취향이 실제 일정에 어느 정도 반영되었는지 계산합니다.

```text
원영       100%
민수       100%
지수       100%
```

이 값은 LLM이 임의로 생성하는 값이 아니라 다음 정보를 기반으로 계산됩니다.

```text
사용자의 선호 카테고리
        ↓
일정에 선택된 장소 카테고리
        ↓
일치한 카테고리 수 계산
        ↓
Preference Reflection
```

취향 데이터가 없는 사용자는 잘못된 0%로 표시하지 않고 다음과 같이 별도로 처리합니다.

```text
취향 데이터 없음
```

---

### 4.12 Multi-day Itinerary

여러 날짜로 구성된 여행도 날짜별로 독립적인 일정을 저장할 수 있습니다.

```text
Day 1
2026-09-20

Day 2
2026-09-21
```

각 날짜는 `day_number`를 기준으로 독립적으로 저장됩니다.

같은 날짜의 일정을 다시 생성하면 기존 일정이 중복 누적되지 않고 해당 날짜의 일정만 교체됩니다.

```text
Day 1 재생성
→ Day 1만 갱신
→ Day 2 유지
```

현재는 날짜별 장소 중복 방지 로직이 적용되지 않아 여러 날짜에 동일한 장소가 선택될 수 있으며, 이는 향후 개선할 예정입니다.

---

### 4.13 Kakao Map

생성된 일정의 실제 위치를 Kakao Map에서 확인할 수 있습니다.

지도에는 일정에 포함된 장소의 좌표와 방문 순서를 표시합니다.

```text
1 → 2 → 3 → 4
```

현재 지도 연결선은 일정 방문 순서를 표현하며 실제 도로 경로나 이동 시간을 의미하지 않습니다.

---

## 5. Service Flow

```text
1. 사용자 생성
        ↓
2. 여행방 생성
        ↓
3. 여행 멤버 추가
        ↓
4. 각자 YouTube Shorts URL 저장
        ↓
5. YouTube 메타데이터 수집
        ↓
6. AI 콘텐츠 분석
        ↓
7. 장소 / 지역 / 카테고리 / 키워드 구조화
        ↓
8. Kakao 실제 장소 검증
        ↓
9. 개인 Preference DB 업데이트
        ↓
10. AI 분석 결과 사용자 확인 및 수정
        ↓
11. Shared Trip Basket
        ↓
12. Group Preference Analysis
        ↓
13. Kakao 장소 후보 탐색
        ↓
14. Preference-aware 일정 생성
        ↓
15. 사용자별 취향 반영도 계산
        ↓
16. Kakao Map 일정 표시
```

---

## 6. AI Pipeline

TripClip의 AI 기능은 크게 두 단계로 구성됩니다.

### AI 1. Content & Preference Analyzer

담당: 조원영

```text
YouTube Shorts
        ↓
메타데이터 수집
        ↓
LLM 분석
        ↓
장소 / 지역 / 카테고리 / 키워드 추출
        ↓
단일 장소 / 모음형 콘텐츠 구분
        ↓
Kakao 실제 장소 검증
        ↓
사용자 확인 및 수정
        ↓
Personal Preference DB
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

LLM 출력은 Pydantic schema를 통해 검증하며, 실패 시 rule-based analyzer로 fallback할 수 있도록 구성했습니다.

---

### AI 2. Group Preference & Itinerary Planner

담당: 김주하

```text
Personal Preference DB
+
여행방 멤버
+
Kakao 장소 후보
+
날짜 / 시간 / 지역
        ↓
Group Preference Analysis
        ↓
사용자별 장소 적합도 계산
        ↓
Preference Balancing
        ↓
Fairness-aware Place Selection
        ↓
Shared Itinerary
        ↓
Preference Reflection
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

현재 구현된 MVP의 핵심 흐름은 다음과 같습니다.

```text
숏폼 URL 입력
        ↓
AI 콘텐츠 분석
        ↓
실제 장소 검증
        ↓
사용자 확인 및 수정
        ↓
Personal Preference DB
        ↓
Shared Trip Basket
        ↓
Group Preference
        ↓
AI 공동 일정 생성
        ↓
Preference Reflection
        ↓
Kakao Map
```

### Implemented

- 여행방 생성
- 여행방 멤버 관리
- 사용자별 YouTube Shorts 등록
- AI 콘텐츠 구조화
- 단일 장소와 모음형 콘텐츠 구분
- Kakao 실제 장소 검증
- AI 분석 결과 확인 및 수정
- 개인 취향 분석
- Shared Trip Basket
- 그룹 취향 분석
- Preference-aware 일정 생성
- 사용자 간 fairness 적용
- 추천 이유 표시
- 사용자별 취향 반영도 계산
- Kakao Map 일정 표시
- 같은 날짜 일정 재생성
- Multi-day 일정 저장
- 취향 데이터가 없는 멤버 처리

### In Progress

- 회원가입 Frontend
- 로그인 및 인증
- 현재 로그인 사용자 기반 서비스 흐름
- 공개 서버 배포

### Future Work

- 날짜 간 중복 장소 방지
- 실제 이동 거리 및 이동 시간 계산
- Instagram Reels 실제 연동
- TikTok 실제 연동
- 일정 수정 요청
- 소셜 로그인
- 친구 초대 및 공유 기능
- 취향 분석 시각화 개선

---

## 8. System Architecture

```text
┌─────────────────────────────────────┐
│              Frontend               │
│                                     │
│ Next.js / React / TypeScript        │
│                                     │
│ Trip / Shortform / Preference       │
│ Basket / Itinerary / Map            │
└─────────────────┬───────────────────┘
                  │
                  │ REST API
                  ▼
┌─────────────────────────────────────┐
│              Backend                │
│                                     │
│ FastAPI / SQLAlchemy                │
│                                     │
│ User / Trip / Member                │
│ Shortform / Preference / Itinerary  │
└───────┬─────────────┬───────────────┘
        │             │
        │             │
        ▼             ▼
┌───────────────┐   ┌───────────────────┐
│     AI 1      │   │       AI 2        │
│               │   │                   │
│ Content &     │   │ Group Preference  │
│ Preference    │   │ & Itinerary       │
│ Analyzer      │   │ Planner           │
└───────┬───────┘   └─────────┬─────────┘
        │                     │
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │        MySQL        │
        │                     │
        │ User / Trip         │
        │ Content / Preference│
        │ Place / Itinerary   │
        └─────────────────────┘

External Services

YouTube oEmbed
Kakao Local API
Kakao Maps JavaScript API
Kookmin University LLM API
```

---

## 9. Team

| Role | Member | Responsibility |
|---|---|---|
| PM / AI 1 | 조원영 | 프로젝트 전체 일정 및 개발 방향 관리, 파트 간 기능 통합, 숏폼 콘텐츠 분석, 장소 구조화, 사용자 취향 데이터 생성 |
| AI 2 | 김주하 | 그룹 취향 분석, 사용자 간 취향 조율, 장소 후보 평가, 공동 일정 생성, 취향 반영도 계산 |
| Frontend 1 | 최연하 | 여행방 생성 및 참가, 숏폼 URL 입력, AI 분석 결과 확인 및 수정 UI |
| Frontend 2 | 임재민 | Shared Trip Basket, 그룹 취향 분석, 일정 생성 및 결과, Kakao Map, 취향 반영 UI |
| Backend | 최우혁 | 사용자, 여행방, 멤버, 콘텐츠, 취향, 일정 API 및 MySQL 데이터 관리 |

---

## 10. Development Roles

### PM / AI 1 — 조원영

프로젝트 전체 개발 흐름을 관리하고 각 파트에서 개발한 기능을 하나의 서비스로 통합합니다.

주요 담당 업무는 다음과 같습니다.

- 프로젝트 개발 방향 및 우선순위 관리
- Frontend, Backend, AI 간 기능 및 데이터 흐름 조율
- Full-stack 통합
- End-to-End 테스트
- YouTube Shorts 메타데이터 분석 파이프라인 구성
- LLM 기반 숏폼 콘텐츠 분석
- 장소명, 지역, 카테고리, 활동, 키워드 추출
- 단일 장소와 모음형 콘텐츠 구분
- AI 응답 검증 및 parser fallback 구성
- Kakao 장소 검증 로직과 콘텐츠 분석 결과 연결
- 사용자 Preference 생성 및 업데이트
- 서비스 전체 통합 검증

### AI 2 — 김주하

사용자별 취향 데이터를 바탕으로 그룹 취향을 분석하고 공동 일정을 생성합니다.

주요 담당 업무는 다음과 같습니다.

- 개인별 Preference Profile 분석
- Group Preference Analysis
- 사용자별 장소 적합도 계산
- 그룹 장소 점수 계산
- 구성원 간 취향 균형 조정
- Kakao 장소 후보 평가
- 공동 일정 생성
- 일정 추천 이유 생성
- 사용자별 취향 반영도 계산
- Fairness-aware Place Selection

### Frontend 1 — 최연하

사용자가 여행방을 만들고 숏폼 콘텐츠를 등록하는 초기 서비스 흐름을 담당합니다.

주요 담당 업무는 다음과 같습니다.

- 메인 화면
- 여행방 생성
- 여행방 참가
- 숏폼 URL 입력
- AI 분석 결과 확인
- AI 분석 결과 수정
- 콘텐츠 저장 및 수정 UI

### Frontend 2 — 임재민

저장된 콘텐츠와 취향 데이터를 시각화하고 일정 생성 및 결과 화면을 담당합니다.

주요 담당 업무는 다음과 같습니다.

- Shared Trip Basket
- 사용자별 저장 콘텐츠 표시
- Group Preference UI
- 여행 조건 입력
- 공동 일정 생성 UI
- 일정 결과 표시
- 사용자별 취향 반영 근거 표시
- Kakao Map 기반 일정 위치 표시
- Preference Reflection UI
- 취향 데이터가 없는 사용자 처리

### Backend — 최우혁

서비스 API와 데이터베이스를 관리하고 Frontend와 AI 기능을 연결합니다.

주요 담당 업무는 다음과 같습니다.

- 사용자 관리 API
- 여행방 관리 API
- 여행 멤버 관리 API
- 숏폼 콘텐츠 저장 및 수정 API
- AI 모듈 연결
- Kakao Local API 연결
- 장소 데이터 저장 및 관리
- 사용자 Preference DB 관리
- Group Preference 조회 API
- 일정 생성 및 조회 API
- MySQL 데이터 영속화

---

## 11. Repository Structure

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
│   ├── tests/
│   ├── public/
│   ├── package.json
│   └── pnpm-lock.yaml
│
├── requirements.txt
├── SPEC.md
├── .gitignore
└── README.md
```

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
- Pydantic structured output validation
- Rule-based parser fallback
- Custom Preference Analyzer
- Group Preference Analysis
- Preference-aware Itinerary Planner
- Fairness-aware Place Selection

### Database

- MySQL 8
- InnoDB
- utf8mb4
- JSON columns
- UUID 기반 내부 ID

### External API

- YouTube oEmbed
- 국민대학교 OpenAI-compatible LLM API
- Kakao Local API
- Kakao Maps JavaScript API

### Deployment

현재 로컬 Full-stack 통합 및 End-to-End 검증을 완료했으며 공개 배포를 준비하고 있습니다.

예정 구조는 다음과 같습니다.

```text
Frontend
Next.js
        ↓
Backend
FastAPI
        ↓
MySQL

External
Kakao / YouTube / LLM API
```

---

## 13. Database Structure

주요 테이블은 다음과 같습니다.

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

Kakao provider ID는 TripClip 내부 UUID로 변환하여 `place_id`로 관리합니다.

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

Backend는 다음 환경변수를 사용합니다.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=tripclip_dev

LLM_API_KEY=
LLM_BASE_URL=https://ai.cs.kookmin.ac.kr/v1
LLM_MODEL=claude-sonnet-4-5

KAKAO_REST_API_KEY=
```

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

## 16. Local Run

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

기존 DB에는 migration을 순서대로 적용합니다.

```text
backend/db/migrations/
├── 001_backend_schema_alignment.sql
├── 002_ai_persistence.sql
└── 003_shortform_place_verification.sql
```

---

## 18. Verification

### Backend

```cmd
python -m unittest discover -s backend/tests -t . -v
```

현재 통합 기준 결과

```text
Ran 59 tests

OK (skipped=1)
```

검증 범위는 다음을 포함합니다.

- User
- Trip
- Member
- Shortform
- Preference
- Kakao Place Provider
- Itinerary
- Fairness regression
- Same-day regeneration
- Multi-day isolation
- No-preference member

---

### Frontend Tests

현재 Frontend 관련 테스트는 다음을 검증합니다.

- Backend Itinerary response adapter
- Multi-day itinerary contract
- Preference reflection
- 취향 데이터가 없는 사용자 처리

현재 결과

```text
15 tests passed
```

---

### ESLint

```cmd
cd web
pnpm exec eslint src
```

현재 결과

```text
0 errors
2 warnings
```

현재 warning은 React Hook Form `watch()`와 React Compiler memoization 관련 경고입니다.

---

### TypeScript

```cmd
cd web
pnpm exec tsc --noEmit
```

현재 결과

```text
PASS
```

---

## 19. Full-stack Integration Status

현재 실제 Frontend와 Backend를 함께 실행하여 다음 흐름을 검증했습니다.

```text
Frontend
        ↓
FastAPI
        ↓
YouTube oEmbed
        ↓
LLM
        ↓
Content Analyzer
        ↓
Kakao Local
        ↓
MySQL
        ↓
Frontend Review
        ↓
사용자 수정
        ↓
Preference Recalculation
        ↓
Group Preference
        ↓
Itinerary Planner
        ↓
Kakao Map
```

검증 완료 기능

- 실제 Backend 사용자 조회
- 여행방 생성
- 멤버 추가
- YouTube Shorts 저장
- LLM 콘텐츠 분석
- 모음형 콘텐츠와 단일 장소 구분
- Kakao 실제 장소 검색
- 주소 및 좌표 저장
- `shortform_contents.place_id`와 `places` 연결
- AI 분석 결과 수정
- PATCH 저장
- 수정 후 Preference 재계산
- Shared Trip Basket
- Group Preference
- 실제 Kakao 후보 기반 일정 생성
- Preference fairness
- Preference reflection
- Kakao Map
- 일정 새로고침 복원
- 같은 날짜 일정 재생성
- Multi-day 일정 독립 저장
- 특정 날짜 재생성 시 다른 날짜 일정 보존
- 취향 데이터가 없는 사용자 처리

---

## 20. Verified Scenarios

### Place Verification

```text
AI 장소명
이리에 라멘

Kakao 장소명
이리에라멘

주소
서울 마포구 성지1길 18

결과
실제 장소 검증 성공
```

```text
AI 장소명
담택

Kakao 장소명
담택 본점

결과
지점명 차이를 처리하여 실제 장소 검증 성공
```

---

### Fairness

테스트 사용자

```text
푸드테스터
food = 1.0

관광테스터
sightseeing = 1.0

전시테스터
exhibition = 1.0
```

생성 결과

```text
서울숲 곤충식물원
→ sightseeing

언더스탠드에비뉴 아트스탠드
→ exhibition

대성갈비
→ food
```

최종 Preference Reflection

```text
푸드테스터       100%
관광테스터       100%
전시테스터       100%
```

---

### Same-day Regeneration

```text
Day 1 일정 생성
→ 4개 장소

Day 1 재생성
→ 기존 일정 교체
→ 장소 4개 유지
→ 8개로 중복 누적되지 않음
```

---

### Multi-day

```text
Day 1
2026-09-20

Day 2
2026-09-21
```

DB에서 두 날짜가 서로 다른 itinerary로 저장되는 것을 확인했습니다.

Day 1을 재생성한 경우

```text
Day 1 updated_at 변경
Day 2 updated_at 유지
```

를 확인했습니다.

---

### No Preference Member

취향 데이터가 없는 사용자를 포함한 여행에서도 일정 생성이 정상 동작합니다.

```text
무취향테스터
Preference Coverage = 0

Preference Reflection
total_categories = 0
matched_categories = []
preference_reflection_percent = null
```

Frontend에서는 다음과 같이 표시합니다.

```text
취향 데이터 없음
```

취향 데이터가 있는 다른 사용자들의 Reflection 계산은 정상적으로 유지됩니다.

---

## 21. Current Development Status

현재 핵심 Full-stack MVP는 통합이 완료된 상태입니다.

```text
Shortform
✅

AI Content Analysis
✅

Kakao Place Verification
✅

Preference DB
✅

Shared Basket
✅

Group Preference
✅

AI Itinerary
✅

Fairness
✅

Preference Reflection
✅

Kakao Map
✅

Multi-day Persistence
✅

Frontend ↔ Backend Integration
✅
```

현재 다음 단계는 서비스 공개를 위한 사용자 인증 및 배포입니다.

```text
회원가입 Frontend
        ↓
로그인 / 인증
        ↓
현재 로그인 사용자 기반 서비스 전환
        ↓
배포 환경 구성
        ↓
MySQL 배포
        ↓
Backend 배포
        ↓
Frontend 배포
        ↓
Production E2E Test
```

---

## 22. Remaining Work

### Authentication

현재 Backend에는 사용자 생성 API와 bcrypt 기반 비밀번호 해싱이 구현되어 있습니다.

```text
POST /api/users
```

다음 단계에서 추가할 예정입니다.

- 회원가입 Frontend
- 로그인 API
- JWT 기반 인증
- 현재 사용자 조회
- 로그아웃
- 로그인 사용자 기반 여행 생성 및 콘텐츠 저장

---

### Deployment

공개 서버 배포를 진행할 예정입니다.

배포 시 필요한 항목은 다음과 같습니다.

- MySQL
- FastAPI Backend
- Next.js Frontend
- Kakao API 환경변수
- LLM API 환경변수
- CORS 설정
- Production End-to-End Test

---

### Itinerary Improvements

현재 Multi-day 일정은 날짜별로 독립 저장되지만 같은 장소가 여러 날짜에 다시 선택될 수 있습니다.

향후 다음 기능을 추가할 예정입니다.

```text
이전 날짜 방문 장소
        ↓
후속 날짜 후보 선택 시 penalty
        ↓
새로운 장소 우선 선택
```

---

## 23. Difference

TripClip은 숏폼에서 장소를 추출하여 여행 일정을 만드는 것만을 목표로 하지 않습니다.

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
→ 콘텐츠 분석
→ 실제 장소 검증
→ Personal Preference DB
→ Group Preference
→ Preference Balancing
→ 공동 일정
→ Preference Reflection
```

핵심 차별점은 다음과 같습니다.

> 장소를 정리하는 것이 아니라 사람들의 취향을 조율한다.

---

## 24. Goal

TripClip의 최종 목표는 사용자가 여행 취향을 직접 일일이 입력하지 않아도, 평소 저장하고 공유하는 콘텐츠를 통해 자연스럽게 취향을 파악하는 것입니다.

그리고 여러 사람이 함께 여행이나 약속을 계획할 때 각자의 관심사를 AI가 분석하여 특정 한 사람에게 계획 부담이 집중되지 않도록 지원합니다.

> Save what you like.  
> Share what you want.  
> Plan together.

---

## Contributors

### 2026 KOSSCCTHON Team 7 (111)

- 조원영 — PM / AI 1
- 김주하 — AI 2
- 최연하 — Frontend 1
- 임재민 — Frontend 2
- 최우혁 — Backend