import type { Itinerary, ItineraryItem, ItineraryRequest } from '@/lib/types'
import { sleep } from '@/lib/api/http'
import { categoryLabel } from '@/lib/categories'
import { getTripMock } from './trips'
import { getGroupPreferencesMock } from './preferences'
// FE1의 GET /trips/{tripId}/contents(C-03)가 나오기 전까지 fe2 임시 fixture를 사용한다.
import { getTripContents } from '@/components/fe2/temp-contents'

// SPEC 6장 시드: 성수동 실제 좌표, 카페 2곳·전시 1곳·쇼핑 1곳 이상, 모든 유저 반영도 1개 이상.
const SEED_PLACES: Array<{
  name: string
  address: string
  lat: number
  lng: number
  category: ItineraryItem['category']
  durationMinutes: number
  reasonTemplate: (names: string[]) => string
  users: (memberIds: string[]) => string[] // 참여 유저 id, 실제 멤버가 있을 때만 반영
}> = [
  {
    name: '성수 팝업스토어',
    address: '서울 성동구 아차산로 1길',
    lat: 37.5445,
    lng: 127.0559,
    category: 'shopping',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 팝업 및 쇼핑 취향을 반영했습니다.`,
    users: (ids) => ids.slice(1, 2), // 민수(두 번째 멤버) 취향
  },
  {
    name: '성수 전시회',
    address: '서울 성동구 연무장길',
    lat: 37.5443,
    lng: 127.0567,
    category: 'exhibition',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 전시 취향을 반영했습니다.`,
    users: (ids) => ids.slice(2, 3).concat(ids.slice(0, 1)), // 지수 + 원영
  },
  {
    name: '성수 브런치 카페',
    address: '서울 성동구 성수이로',
    lat: 37.5447,
    lng: 127.0578,
    category: 'cafe',
    durationMinutes: 75,
    reasonTemplate: (names) => `${names.join(', ')}의 카페 취향을 반영했습니다.`,
    users: (ids) => ids.slice(0, 1), // 원영
  },
  {
    name: '성수 디저트 카페',
    address: '서울 성동구 서울숲2길',
    lat: 37.5466,
    lng: 127.0453,
    category: 'cafe',
    durationMinutes: 75,
    reasonTemplate: (names) => `${names.join(', ')}의 카페 취향을 반영했습니다.`,
    users: (ids) => ids.slice(2, 3), // 지수
  },
  {
    name: '성수 일식집',
    address: '서울 성동구 왕십리로',
    lat: 37.5417,
    lng: 127.0558,
    category: 'food',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 음식 취향을 반영했고, 그룹의 저녁 식사 조건을 충족했습니다.`,
    users: (ids) => ids.slice(0, 1), // 원영
  },
]

function addMinutes(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number)
  const total = h * 60 + m + minutes
  const wrapped = ((total % (24 * 60)) + 24 * 60) % (24 * 60)
  const nh = Math.floor(wrapped / 60)
  const nm = wrapped % 60
  return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`
}

// ---- 최신 일정 저장소 (mock 전용). 새로고침 후 GET /trips/{id}/itinerary 복원용 ----
const STORAGE_KEY = 'tripclip:mock:itineraries'
const memory = new Map<string, Itinerary>()

function load(): Map<string, Itinerary> {
  if (memory.size === 0 && typeof window !== 'undefined') {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (raw) {
        for (const [tripId, it] of Object.entries(JSON.parse(raw) as Record<string, Itinerary>)) {
          memory.set(tripId, it)
        }
      }
    } catch {
      // 저장값이 깨졌으면 무시하고 빈 상태로 시작
    }
  }
  return memory
}

function persist() {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(memory)))
  } catch {
    // 저장 실패는 데모 동작에 영향 없음
  }
}

// GET /trips/{tripId}/itinerary — 없으면 null (실 API의 404와 동일하게 취급)
export async function getTripItineraryMock(tripId: string): Promise<Itinerary | null> {
  await sleep(300 + Math.random() * 400)
  return load().get(tripId) ?? null
}

export async function postGroupItineraryMock(tripId: string, request: ItineraryRequest): Promise<Itinerary> {
  await sleep(1600 + Math.random() * 900)

  const trip = await getTripMock(tripId)
  const group = await getGroupPreferencesMock(tripId)
  const contents = await getTripContents(tripId)
  const memberIds = trip.members.map((m) => m.userId)
  const nameById = new Map(trip.members.map((m) => [m.userId, m.name]))

  const basePlaces = request.includeMeals
    ? SEED_PLACES
    : SEED_PLACES.filter((p) => p.category !== 'food')

  let cursor = request.startTime || '13:00'
  const seedItems: ItineraryItem[] = basePlaces.map((place, index) => {
    const startTime = cursor
    const endTime = addMinutes(startTime, place.durationMinutes)
    cursor = endTime
    const userIds = place.users(memberIds).filter((id): id is string => Boolean(id) && memberIds.includes(id))
    const names = userIds.map((id) => nameById.get(id) ?? id)
    return {
      order: index + 1,
      startTime,
      endTime,
      place: { name: place.name, address: place.address, lat: place.lat, lng: place.lng, verified: true },
      category: place.category,
      reason: place.reasonTemplate(names),
      relatedUsers: userIds.map((id) => ({
        userId: id,
        preferenceKey: place.category,
        preferenceLabel: categoryLabel(place.category),
      })),
    }
  })

  // 사용자가 장바구니에서 고른 필수 장소를 마지막에 덧붙인다.
  const mustVisitItems: ItineraryItem[] = request.mustVisitContentIds
    .map((contentId) => contents.find((c) => c.contentId === contentId))
    .filter((c): c is NonNullable<typeof c> => Boolean(c))
    .map((content, i) => {
      const startTime = cursor
      const endTime = addMinutes(startTime, 60)
      cursor = endTime
      const ownerName = nameById.get(content.userId) ?? content.userId
      return {
        order: seedItems.length + i + 1,
        startTime,
        endTime,
        place: content.place,
        category: content.category,
        contentId: content.contentId,
        reason: `${ownerName}님이 저장한 장소를 필수 코스로 포함했습니다.`,
        relatedUsers: [
          { userId: content.userId, preferenceKey: content.category, preferenceLabel: categoryLabel(content.category) },
        ],
      } satisfies ItineraryItem
    })

  const items = [...seedItems, ...mustVisitItems]

  // 반영도는 "서버"가 계산한다(SPEC 5-3). 프론트 컴포넌트는 이 값을 그대로 표시만 한다.
  const reflection = trip.members.map((member) => {
    const top = group.members.find((m) => m.userId === member.userId)?.top ?? []
    const coveredKeys = new Set<string>(
      items.filter((item) => item.relatedUsers.some((u) => u.userId === member.userId)).map((item) => item.category),
    )
    const coveredTop = top.filter((p) => coveredKeys.has(p.key)).length
    const totalTop = top.length || 1
    return {
      userId: member.userId,
      name: member.name,
      reflectionPercent: Math.round((coveredTop / totalTop) * 100),
      coveredTop,
      totalTop,
    }
  })

  const allMembersCovered = trip.members.every((member) =>
    items.some((item) => item.relatedUsers.some((u) => u.userId === member.userId)),
  )

  const itinerary: Itinerary = {
    itineraryId: `it${Date.now().toString(36)}`,
    tripId,
    days: [{ day: 1, date: trip.startDate, items }],
    reflection,
    allMembersCovered,
    rebalanced: false,
  }

  load().set(tripId, itinerary)
  persist()
  return itinerary
}
