import type { Trip } from '@/lib/types';
import { USE_MOCK } from './config';
import { fetchJson } from './http';
import * as mocks from '@/lib/mocks';

export function createTrip(input: {
  name: string;
  destination: string;
  startDate: string;
  endDate: string;
  memberIds: string[];
}): Promise<Trip> {
  if (USE_MOCK) return mocks.createTrip(input);
  return fetchJson<Trip>('/trips', { method: 'POST', body: JSON.stringify(input) });
}

export function getTrip(tripId: string): Promise<Trip> {
  if (USE_MOCK) return mocks.getTrip(tripId);
  return fetchJson<Trip>(`/trips/${tripId}`);
}
