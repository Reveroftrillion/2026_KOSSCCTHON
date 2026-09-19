# TripClip 프론트엔드 구현 명세서

> **사용법**: 프론트 2명이 각자 AI에게 이 파일 전체를 주고 아래처럼 지시한다.
> "SPEC.md를 읽어라. 나는 **FE1(또는 FE2)** 이다. 7장(또는 8장)의 미완료 작업을 위에서부터 순서대로 진행하고, 끝날 때마다 진행도 표의 상태를 갱신해라."
> 상태 표기: `[ ]` 대기 / `[~]` 진행 중 / `[x]` 완료

---

## 1. 무엇을 만드는가

**TripClip**: 친구들이 SNS(릴스/쇼츠/틱톡)에서 발견한 여행 장소를 한 여행방에 모으면, AI가 모두의 취향을 분석해 **한 사람에게 치우치지 않은 공동 여행 일정**을 만들고 **누구의 어떤 취향이 반영됐는지 근거**를 보여주는 웹 서비스.

**데모 흐름 (이 순서로 화면이 끊김 없이 이어져야 한다)**
1. 여행방 생성(3명) → 2. 각자 숏폼 링크 저장 → 3. AI 분석 결과 확인/수정 → 4. 내 취향 프로필이 쌓임 → 5. 그룹 취향(공통 vs 개인 고유) 확인 → 6. 공동 일정 생성 → 7. 일정 항목별 반영 사용자·이유, 사람별 반영도 확인

**MVP 제외 (만들지 말 것)**: 로그인/회원가입, 결제·예약, SNS 저장목록 자동 불러오기, 최단경로/이동시간 최적화, 장기 학습 추천 모델, 영상 원본 분석

---

## 2. 기술 스택

| 구분 | 선택 |
|---|---|
| 프레임워크 | Next.js 14+ (App Router), TypeScript strict, pnpm |
| UI | Tailwind CSS, shadcn/ui, lucide-react |
| 서버 상태 | TanStack Query |
| 폼 | react-hook-form + zod |
| 지도 | Kakao Maps JS SDK (`react-kakao-maps-sdk`) |
| 인증 | 없음. 데모 유저 3명 중 선택하는 전환 UI |
| 백엔드/AI | **[팀 확정값 기입]** — 프론트는 5장 REST 계약에만 의존 |

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=true
NEXT_PUBLIC_KAKAO_MAP_KEY=
```

---

## 3. 작업 규칙 (AI 필수 준수)

1. **내 역할의 파일만 수정**한다(4장 소유권). 공통 파일(`lib/types.ts`, `lib/api/*`, `lib/mocks/*`)은 **필드/함수 추가만** 허용하고, 변경 시 사용자에게 알린다.
2. **모든 API 호출은 `lib/api/*` 함수를 통한다.** `NEXT_PUBLIC_USE_MOCK=true`이면 백엔드 없이 `lib/mocks`로 동작해야 한다(6장).
3. **점수·반영도를 프론트에서 계산하지 않는다.** 서버 값(`normalized`, `reflectionPercent`)만 표시한다. 원점수(`score`)는 화면에 노출하지 않는다.
4. 모든 화면에 **로딩 / 빈 상태 / 에러(재시도)** 를 넣는다. AI 호출은 수 초 걸린다.
5. 모바일(390px)에서 가로 스크롤이 없어야 한다.
6. 작업 단위마다 `pnpm lint && pnpm build`가 통과해야 완료로 표시한다.
7. 명세에 없는 결정(스택, 필드, API)은 임의로 정하지 말고 사용자에게 묻는다.

---

## 4. 폴더 구조와 소유권

```
src/
├─ app/
│  ├─ page.tsx                                      [FE2] 랜딩 + 데모 유저 선택
│  ├─ trips/new/page.tsx                            [FE2] 여행방 생성
│  ├─ trips/[tripId]/layout.tsx                     [FE2] 상단 정보 + 탭(담기/장바구니/그룹취향/일정)
│  ├─ trips/[tripId]/page.tsx                       [FE2] 여행방 홈
│  ├─ trips/[tripId]/group/page.tsx                 [FE2] 그룹 취향
│  ├─ trips/[tripId]/itinerary/page.tsx             [FE2] 일정 생성·결과
│  ├─ trips/[tripId]/add/page.tsx                   [FE1] 숏폼 저장
│  ├─ trips/[tripId]/review/[contentId]/page.tsx    [FE1] AI 분석 확인/수정
│  ├─ trips/[tripId]/basket/page.tsx                [FE1] 여행 장바구니
│  └─ me/preferences/page.tsx                       [FE1] 개인 취향 프로필
├─ components/
│  ├─ ui/ , common/   [공통, FE1이 세팅] shadcn, Header, LoadingSteps, EmptyState, ErrorState, PreferenceBar, UserAvatar
│  ├─ fe1/            [FE1 전용]
│  └─ fe2/            [FE2 전용] MapView, ItineraryCard 등
└─ lib/
   ├─ types.ts, api/, mocks/, user-context.tsx        [공통, FE1이 세팅]
```

**의존 순서**: FE1이 공통 기반(C-01~C-05)을 먼저 끝내 FE2의 블로커를 없앤다. FE2는 그 전까지 5장 타입에 맞춘 임시 fixture로 자기 화면을 개발하고, 공통 API가 나오면 교체한다.

---

## 5. 데이터 타입과 API 계약

### 5-1. 타입 (`lib/types.ts`에 그대로 작성)

```ts
export type Category = 'cafe' | 'food' | 'exhibition' | 'shopping' | 'sightseeing' | 'activity';
export type TimeSlot = 'morning' | 'afternoon' | 'evening' | 'night';

export interface User { userId: string; name: string }

export interface Trip {
  tripId: string; name: string; destination: string;
  startDate: string; endDate: string;            // YYYY-MM-DD
  members: User[];
}

export interface PlaceInfo {
  name: string; address?: string; lat?: number; lng?: number;
  verified: boolean;                             // 장소 API로 실존 확인 여부
  openHours?: string;
}

export interface Content {                       // 숏폼 1건의 분석 결과
  contentId: string; tripId: string; userId: string;
  url: string; platform: 'instagram' | 'youtube' | 'tiktok' | 'other';
  place: PlaceInfo; category: Category; area: string;
  tags: string[];                                // 예: ['디저트','데이트','감성']
  activityType?: string; mood?: string; recommendedTime?: TimeSlot;
  confidence: number;                            // 0~1
  userEdited: boolean; savedAt: string;
}

export interface PreferenceItem {
  key: string; label: string; type: 'category' | 'tag';
  score: number;                                 // 원점수 (화면 노출 금지)
  normalized: number;                            // 0~100, 해당 유저 최고=100
  evidenceCount: number;
}
export interface UserPreferences { userId: string; top: PreferenceItem[]; all: PreferenceItem[] }

export interface GroupPreferences {
  members: { userId: string; name: string; top: PreferenceItem[] }[];
  common: { key: string; label: string; memberIds: string[] }[];                 // 2명 이상 공통
  unique: { userId: string; key: string; label: string; normalized: number }[];  // 개인 고유(강함)
  matrix: { userIds: string[]; keys: string[]; values: number[][] };             // values[user][key]
}

export interface ItineraryRequest {
  area: string; startTime: string; endTime: string;  // 'HH:mm'
  budget?: number; includeMeals: boolean; mustVisitContentIds: string[];
}
export interface ItineraryItem {
  order: number; startTime: string; endTime: string;
  place: PlaceInfo; category: Category; contentId?: string;
  reason: string;                                    // 추천 이유
  relatedUsers: { userId: string; preferenceKey: string; preferenceLabel: string }[];
}
export interface Itinerary {
  itineraryId: string; tripId: string;
  days: { day: number; date: string; items: ItineraryItem[] }[];
  reflection: { userId: string; name: string; reflectionPercent: number;
                coveredTop: number; totalTop: number }[];   // 서버 계산값
  allMembersCovered: boolean;                        // 모든 구성원 취향이 1회 이상 반영됐는가
  rebalanced: boolean;                               // 균형 보정 재생성 여부
}
```

### 5-2. API (`group_id == trip_id`)

| Method & Path | 용도 | 요청 → 응답 | 담당 |
|---|---|---|---|
| `POST /contents` | 숏폼 분석·저장 | `{url, userId, tripId, note?}` → `Content` | FE1 |
| `PATCH /contents/{contentId}` * | 분석 결과 수정 | `Partial<Content>` → `Content` | FE1 |
| `GET /trips/{tripId}/contents` * | 장바구니 | → `Content[]` | FE1 |
| `GET /users/{id}/preferences` | 개인 취향 | → `UserPreferences` | FE1 |
| `POST /trips` * | 여행방 생성 | `{name,destination,startDate,endDate,memberIds}` → `Trip` | FE2 |
| `GET /trips/{tripId}` * | 여행방 조회 | → `Trip` | FE2 |
| `GET /groups/{id}/preferences` | 그룹 취향 | → `GroupPreferences` | FE2 |
| `POST /groups/{id}/itinerary` | 일정 생성 | `ItineraryRequest` → `Itinerary` | FE2 |
| `GET /trips/{tripId}/itinerary` * | 최신 일정 조회 | → `Itinerary` | FE2 |

\* 원 기획 문서(4개 API)에 없어 화면 구현용으로 추가 제안한 것. 백엔드와 합의 필요.

### 5-3. 서버가 하는 일 (프론트는 알아만 둔다)
- 취향 점수: 주 카테고리 +3, 세부 태그 +1, 직접 관심 +2, AI 분석 확인 +1. 화면에는 정규화 값만("카페 100 / 전시 72 / 음식 65").
- 일정 생성 파이프라인: Content Parser → Preference Updater → Group Preference Builder → Itinerary Planner → Balance Checker. **일정 로딩 UI 문구는 이 단계를 따른다**(예: "그룹 취향 분석 중 → 일정 생성 중 → 균형 점검 중").
- 반영도는 실제 선택된 일정이 각 사용자의 상위 취향을 몇 개 충족했는지로 서버가 계산한다.

---

## 6. 목(mock) 규칙과 시드 데이터

**규칙**
- `lib/api/*`는 `USE_MOCK`이면 `lib/mocks`를 호출한다. 응답에 `await sleep(500~1500ms)`를 넣어 로딩 UI를 확인할 수 있게 한다.
- **목은 메모리 상태를 유지한다(stateful).** `POST /contents`로 저장하면 콘텐츠 목록에 추가되고 해당 유저의 취향 점수가 실제로 오른다(주 카테고리 +3, 태그 +1). `PATCH`로 수정하면 수정본 기준으로 재계산한다. 정규화는 유저별 최고점=100.
- 일정 생성은 시드의 고정 일정을 반환하되, 저장된 장소가 있으면 `mustVisitContentIds`를 반영해 포함한다.

**시드**
- 유저: `u1=원영`, `u2=민수`, `u3=지수`
- 초기 카테고리 정규화 값

| 사용자 | 카페 | 전시 | 쇼핑 |
|---|---|---|---|
| 원영 | 90 | 40 | 20 |
| 민수 | 30 | 55 | 95 |
| 지수 | 75 | 85 | 35 |

- 기대 해석: 카페=원영·지수 공통 / 쇼핑=민수 고유(강함) / 전시=지수 중심이나 수용 가능
- 콘텐츠 예: `"성수에서 꼭 가봐야 할 디저트 카페 #성수카페 #데이트"` → `cafe`, 지역 `성수`, 태그 `[디저트,데이트,감성]`, `afternoon` → 반영: 카페 +3, 디저트 +1, 데이트 +1, 감성 +1
- 일정 시드: 성수동 실제 좌표 사용, 카페 2곳·전시 1곳·쇼핑 1곳 이상, `allMembersCovered=true`, 모든 유저 반영도 1개 이상 충족

---

## 7. FE1 — 콘텐츠 입력 · AI 분석 · 개인 취향

**목표**: 숏폼을 저장하면 AI 분석 결과를 확인·수정하고, 내 취향이 쌓이는 것을 본다.

### 화면 요구사항

**A. 숏폼 저장** `/trips/[tripId]/add`
- URL 입력(필수, 플랫폼 자동 감지 뱃지), 보정 입력 textarea(게시글 내용/해시태그, 선택)
- 제출 → `POST /contents` → 분석 로딩 → 성공 시 B로 이동. URL 형식 오류·실패 메시지.

**B. AI 분석 확인/수정** `/trips/[tripId]/review/[contentId]`
- 표시: 장소명, 주소, 지역, 카테고리, 태그 칩, 활동 유형, 분위기, 추천 시간대, 신뢰도, **장소 실존 확인(`verified`) 뱃지**
- 수정 가능: 장소명, 카테고리(셀렉트), 태그(추가/삭제), 시간대. 저장 → `PATCH` → `userEdited=true`.
- 저장 후 "취향 DB 반영: cafe +3, 디저트 +1 …" 요약 카드 표시.
- `verified=false`면 경고 배너 + 장소명 수정 유도.

**C. 여행 장바구니** `/trips/[tripId]/basket`
- 전체 멤버가 저장한 장소 카드(장소명·지역·카테고리·태그·저장자 아바타·원본 링크), 카테고리/멤버 필터, 멤버별 저장 개수 요약
- 빈 상태: "첫 숏폼을 담아보세요" → A

**D. 개인 취향 프로필** `/me/preferences`
- `GET /users/{id}/preferences` → 상위 카테고리 가로 막대(정규화 100 기준), 상위 태그 칩(근거 건수)
- 저장 직후 재조회하고 증가한 항목을 하이라이트. 데모 유저 전환 가능.

### 진행도

| ID | 작업 | 상태 | 완료 기준 |
|---|---|---|---|
| C-01 | Next.js+TS+Tailwind+shadcn+TanStack Query 세팅, 4장 폴더 생성 | [x] | `pnpm dev` 실행 |
| C-02 | `lib/types.ts` (5-1 그대로) | [x] | tsc 통과, FE2에 공유 |
| C-03 | `lib/api/*` + stateful `lib/mocks/*` + 시드 (6장) | [x] | 5-2 전 엔드포인트가 mock으로 동작 |
| C-04 | `user-context` + 데모 유저 전환 컴포넌트 | [x] | 전환 시 조회 데이터가 바뀜 |
| C-05 | 공통 컴포넌트 (LoadingSteps, EmptyState, ErrorState, PreferenceBar, UserAvatar, Header) | [x] | FE2가 import 가능 |
| F1-01 | A. 숏폼 저장 화면 | [x] | 제출 → 로딩 → B 이동 |
| F1-02 | B. 분석 결과 표시 (verified·confidence 포함) | [ ] | 모든 필드 표시 |
| F1-03 | B. 수정 + PATCH + 취향 반영 요약 | [ ] | 재조회 시 수정본 유지 |
| F1-04 | C. 장바구니 (필터·저장자 표시) | [ ] | 멤버/카테고리 필터 동작 |
| F1-05 | D. 개인 취향 프로필 + 변화 하이라이트 | [ ] | 숏폼 3건 저장 시 점수 누적이 보임, 원점수 미노출 |
| F1-06 | 로딩/빈/에러 상태, 모바일 점검 | [ ] | 4장 모든 FE1 화면 적용 |
| F1-07 | 실 API 전환(`USE_MOCK=false`) 및 버그 수정 | [ ] | 백엔드 응답으로 전 화면 동작 |

---

## 8. FE2 — 여행방 · 그룹 취향 · 공동 일정

**목표**: 친구들의 취향을 한눈에 비교하고, AI 공동 일정과 **사람별 반영 근거**를 보여준다.

### 화면 요구사항

**A. 랜딩 / 여행방 생성** `/`, `/trips/new`
- 랜딩: 한 줄 소개, 데모 유저 선택, "여행방 만들기" CTA
- 생성 폼: 이름, 목적지, 기간(종료일 ≥ 시작일), 멤버 2~4명 선택 → `POST /trips` → 여행방 홈 이동

**B. 여행방 홈/레이아웃** `/trips/[tripId]`
- 상단: 목적지·기간·멤버 아바타. 탭: 담기 / 장바구니 / 그룹 취향 / 일정 (앞 두 탭은 FE1 페이지로 연결)
- 멤버별 저장 개수 카드, 그룹 분석 가능 여부 안내

**C. 그룹 취향** `/trips/[tripId]/group`
- `GET /groups/{id}/preferences`
- **사용자×카테고리 매트릭스**(히트맵 표)
- **공통 취향**과 **개인 고유 취향**을 색·라벨로 구분해 표시 (예: 카페=공통, 쇼핑=민수)
- 서버 데이터로 해석 문구 조합. CTA "이 취향으로 일정 만들기" → D

**D. 일정 생성·결과** `/trips/[tripId]/itinerary`
- 조건 입력: 지역, 시작/종료 시간, 예산(선택), 식사 포함, 필수 장소(장바구니에서 선택)
- 생성 → `POST /groups/{id}/itinerary` → 단계 로딩 UI(5-3)
- 결과:
  - 일자별 타임라인 카드: 순서·시간·장소·카테고리·**추천 이유**·**반영 사용자 칩**("지수 · 카페")
  - 지도: 마커+순번+직선 연결, 카드↔마커 클릭 연동 (경로 최적화 아님)
  - **사람별 반영도 패널**: `reflectionPercent`, `coveredTop/totalTop` 진행 막대. `allMembersCovered=false`면 경고, `rebalanced=true`면 "균형 보정됨" 뱃지
  - "다시 생성" 버튼, 재진입 시 `GET /trips/{id}/itinerary`로 복원

### 진행도

| ID | 작업 | 상태 | 완료 기준 |
|---|---|---|---|
| F2-01 | A. 랜딩 + 여행방 생성 폼 | [ ] | 생성 후 홈으로 이동, 입력 검증 동작 |
| F2-02 | B. 레이아웃 + 탭 + 여행방 홈 | [ ] | FE1 화면이 탭으로 연결됨 |
| F2-03 | C. 그룹 취향 매트릭스 | [ ] | 3인×카테고리 값 표시 |
| F2-04 | C. 공통 vs 개인 고유 구분 + 해석 문구 + CTA | [ ] | 카페=공통, 쇼핑=민수로 구분 |
| F2-05 | D. 일정 조건 입력 폼 | [ ] | 필수 장소 선택 포함 |
| F2-06 | D. 단계 로딩 UI + 생성 호출 | [ ] | 파이프라인 문구 순차 표시 |
| F2-07 | D. 타임라인 카드 + 추천 이유 + 반영 사용자 칩 | [ ] | 모든 항목에 reason·relatedUsers 표시 |
| F2-08 | D. Kakao 지도 마커·연결선·카드 연동 | [ ] | 마커 클릭 시 카드 포커스 (키 없으면 지도만 비활성) |
| F2-09 | D. 사람별 반영도 패널 + 경고/보정 뱃지 | [ ] | 서버 값만 표시 |
| F2-10 | D. 다시 생성, 재진입 복원, 로딩/빈/에러, 모바일 점검 | [ ] | 새로고침 후 일정 복원 |
| F2-11 | 실 API 전환(`USE_MOCK=false`) 및 버그 수정 | [ ] | 백엔드 응답으로 전 화면 동작 |

---

## 9. 완료 기준 (데모 전 필수 확인)

- [ ] 숏폼 3건 이상 저장 시 취향 점수가 실제로 누적된다 (FE1)
- [ ] 분석 결과를 수정하면 수정본 기준으로 취향이 반영된다 (FE1)
- [ ] 3명 취향에서 공통 취향과 개인 고유 취향이 구분되어 보인다 (FE2)
- [ ] 일정이 모든 구성원의 취향을 한 번 이상 반영한다 (FE2)
- [ ] 각 장소에 추천 이유와 관련 사용자가 표시된다 (FE2)
- [ ] 같은 데모 데이터로 여러 번 실행해도 1장 데모 흐름이 안정적으로 동작한다 (공통, `USE_MOCK` 폴백 포함)

---

## 10. 팀 확정 필요 항목 (AI가 임의로 정하지 말고 질문할 것)

1. 백엔드/AI 스택과 `API_BASE_URL`
2. 엔티티 명칭: 기획서는 `Trip/TripMember/Place/SavedPlace`, 취향 DB 보고서는 `Group/GroupMember/Content/Itinerary`. 이 명세는 `Trip = Group`, `Content = SavedPlace`로 통합함
3. 5-2의 `*` 표시 추가 엔드포인트 확정 여부
4. 지도 SDK(Kakao 가정) 및 장소 검색 API
5. 초대 방식(데모 유저 선택 vs 초대 링크)