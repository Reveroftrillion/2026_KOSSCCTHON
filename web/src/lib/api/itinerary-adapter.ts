import type { Itinerary, ItineraryRequest, Trip } from '@/lib/types'

export interface BackendItinerary {
  itinerary_id: string
  trip_id: string
  date: string
  day_number: number
  time_range: string
  summary?: string
  place_source: string
  schedule: {
    time: string; place_id: string; place: string; category: string; reason: string
    related_users: string[]; user_scores: Record<string, number>; group_score: number
    latitude?: number | string | null; longitude?: number | string | null; address?: string | null
  }[]
  preference_coverage: Record<string, number>
  preference_reflection: NonNullable<Itinerary['preferenceReflection']>
  unverifiable_conditions?: string[]
}

export function toBackendRequest(request: ItineraryRequest, trip: Trip) {
  const date = request.date ?? trip.startDate
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date < trip.startDate || date > trip.endDate) {
    throw new Error('여행 기간 안의 날짜를 선택해 주세요.')
  }
  // The Backend uses the trip DB region/time; never silently discard edits.
  if (request.area !== trip.destination || request.startTime !== trip.dayStartTime || request.endTime !== trip.dayEndTime) {
    throw new Error('지역·시간은 여행방 설정을 사용해요. 여행 정보를 새로 불러와 주세요.')
  }
  if (request.mustVisitContentIds.length) throw new Error('필수 장소 지정은 아직 지원하지 않아요.')
  const conditions: string[] = []
  if (request.includeMeals) conditions.push('저녁 식사 포함')
  if (request.budget != null) conditions.push(`1인 예산 ${request.budget}원 이하`)
  return { date, user_conditions: conditions }
}

function coordinate(value: number | string | null | undefined, max: number): number | undefined {
  if (value == null || value === '') return undefined
  const number = Number(value)
  return Number.isFinite(number) && Math.abs(number) <= max ? number : undefined
}

export function fromBackendItinerary(raw: BackendItinerary, trip: Trip): Itinerary {
  if (!Array.isArray(raw.schedule)) throw new Error('이전 형식의 일정입니다. 새 일정을 생성해 주세요.')
  if (raw.place_source === 'mock') throw new Error('샘플 장소로 생성된 일정입니다. Backend Kakao 설정을 확인한 뒤 다시 생성해 주세요.')
  const names = new Map(trip.members.map(member => [member.userId, member.name]))
  const coverage = Object.values(raw.preference_coverage)
  return {
    itineraryId: raw.itinerary_id,
    tripId: raw.trip_id,
    days: [{ day: raw.day_number, date: raw.date, items: raw.schedule.map((stop, index) => ({
      order: index + 1,
      startTime: stop.time,
      endTime: raw.schedule[index + 1]?.time ?? raw.time_range.split('~')[1]?.trim() ?? '',
      placeId: stop.place_id,
      place: { name: stop.place, address: stop.address ?? undefined,
        lat: coordinate(stop.latitude, 90), lng: coordinate(stop.longitude, 180), verified: raw.place_source === 'kakao' },
      category: stop.category,
      reason: stop.reason,
      relatedUsers: stop.related_users.map(userId => ({ userId, preferenceKey: '', preferenceLabel: '취향 적합' })),
      userScores: stop.user_scores,
      groupScore: stop.group_score,
    })) }],
    reflection: Object.entries(raw.preference_reflection).map(([userId, value]) => ({
      userId, name: names.get(userId) ?? userId,
      reflectionPercent: value.preference_reflection_percent,
      coveredTop: value.matched_categories.length, totalTop: value.total_categories,
    })),
    allMembersCovered: coverage.length > 0 && coverage.every(score => score > 0),
    rebalanced: false, // Backend does not report a second generation pass.
    preferenceCoverage: raw.preference_coverage,
    preferenceReflection: raw.preference_reflection,
    placeSource: raw.place_source,
    summary: raw.summary,
    unverifiableConditions: raw.unverifiable_conditions,
  }
}
