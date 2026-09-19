import type { Itinerary, ItineraryRequest } from '@/lib/types'
import { postGroupItineraryMock } from '@/lib/mocks/itinerary'
import { http, USE_MOCK } from './http'

// POST /groups/{id}/itinerary (group_id == trip_id, SPEC 5-2)
export function postGroupItinerary(tripId: string, request: ItineraryRequest): Promise<Itinerary> {
  if (USE_MOCK) return postGroupItineraryMock(tripId, request)
  return http<Itinerary>(`/groups/${encodeURIComponent(tripId)}/itinerary`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
