import type { Trip } from '@/lib/types';
import { http, USE_MOCK } from './http';
import * as mocks from '@/lib/mocks';

export function createTrip(input: {
  name: string;
  destination: string;
  startDate: string;
  endDate: string;
  memberIds: string[];
}): Promise<Trip> {
  if (USE_MOCK) return mocks.createTrip(input);
  return http<Trip>('/trips', { method: 'POST', body: JSON.stringify(input) });
}

export function getTrip(tripId: string): Promise<Trip> {
  if (USE_MOCK) return mocks.getTrip(tripId);
  return http<Trip>(`/trips/${encodeURIComponent(tripId)}`);
}
