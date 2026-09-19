import type { Trip } from '@/lib/types'
import { createTripMock, getTripMock, type CreateTripInput } from '@/lib/mocks/trips'
import { http, USE_MOCK } from './http'

export type { CreateTripInput }

// POST /trips
export function createTrip(input: CreateTripInput): Promise<Trip> {
  if (USE_MOCK) return createTripMock(input)
  return http<Trip>('/trips', { method: 'POST', body: JSON.stringify(input) })
}

// GET /trips/{tripId}
export function getTrip(tripId: string): Promise<Trip> {
  if (USE_MOCK) return getTripMock(tripId)
  return http<Trip>(`/trips/${encodeURIComponent(tripId)}`)
}
