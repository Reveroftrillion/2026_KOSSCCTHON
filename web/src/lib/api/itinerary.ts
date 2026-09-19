import type { Itinerary, ItineraryRequest } from '@/lib/types';
import { USE_MOCK } from './config';
import { fetchJson } from './http';
import * as mocks from '@/lib/mocks';

export function createItinerary(groupId: string, request: ItineraryRequest): Promise<Itinerary> {
  if (USE_MOCK) return mocks.createItinerary(groupId, request);
  return fetchJson<Itinerary>(`/groups/${groupId}/itinerary`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function getLatestItinerary(tripId: string): Promise<Itinerary> {
  if (USE_MOCK) return mocks.getLatestItinerary(tripId);
  return fetchJson<Itinerary>(`/trips/${tripId}/itinerary`);
}
