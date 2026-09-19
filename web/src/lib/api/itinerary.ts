import type { Itinerary, ItineraryRequest } from '@/lib/types'
import { http, USE_MOCK } from './http'
import { getTrip } from './trips'
import { fromBackendItinerary, toBackendRequest, type BackendItinerary } from './itinerary-adapter'
import * as mocks from '@/lib/mocks'

export async function postGroupItinerary(tripId: string, request: ItineraryRequest): Promise<Itinerary> {
  if (USE_MOCK) return mocks.createItinerary(tripId, request)
  const trip = await getTrip(tripId)
  const raw = await http<BackendItinerary>(`/api/trips/${encodeURIComponent(tripId)}/itinerary`, {
    method: 'POST', body: JSON.stringify(toBackendRequest(request, trip)),
  })
  return fromBackendItinerary(raw, trip)
}

// Restore the last day in the Backend's day-number ordered list.
export async function getTripItinerary(tripId: string): Promise<Itinerary | null> {
  if (USE_MOCK) return mocks.getLatestItinerary(tripId)
  const base = `/api/trips/${encodeURIComponent(tripId)}/itineraries`
  const saved = await http<BackendItinerary[]>(base)
  if (!saved.length) return null
  const latest = saved[saved.length - 1]
  const [raw, trip] = await Promise.all([
    http<BackendItinerary>(`${base}/${encodeURIComponent(latest.itinerary_id)}`), getTrip(tripId),
  ])
  return fromBackendItinerary(raw, trip)
}
