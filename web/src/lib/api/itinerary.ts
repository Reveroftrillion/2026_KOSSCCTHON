import type { Itinerary, ItineraryRequest } from '@/lib/types'
import { http, HttpError, USE_MOCK } from './http'
import * as mocks from '@/lib/mocks'

// POST /groups/{id}/itinerary (group_id == trip_id, SPEC 5-2)
export function postGroupItinerary(tripId: string, request: ItineraryRequest): Promise<Itinerary> {
  if (USE_MOCK) return mocks.createItinerary(tripId, request)
  return http<Itinerary>(`/groups/${encodeURIComponent(tripId)}/itinerary`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

// GET /trips/{tripId}/itinerary — 최신 일정 조회(재진입 복원, SPEC 5-2 * 항목).
// 아직 생성된 일정이 없으면(404) null을 돌려준다.
export async function getTripItinerary(tripId: string): Promise<Itinerary | null> {
  if (USE_MOCK) return mocks.getLatestItinerary(tripId)
  try {
    return await http<Itinerary>(`/trips/${encodeURIComponent(tripId)}/itinerary`)
  } catch (e) {
    if (e instanceof HttpError && e.status === 404) return null
    throw e
  }
}
