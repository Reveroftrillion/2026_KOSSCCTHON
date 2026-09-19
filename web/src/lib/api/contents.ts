import type { Content } from '@/lib/types';
import { USE_MOCK } from './config';
import { fetchJson } from './http';
import * as mocks from '@/lib/mocks';

export function createContent(input: {
  url: string;
  userId: string;
  tripId: string;
  note?: string;
}): Promise<Content> {
  if (USE_MOCK) return mocks.createContent(input);
  return fetchJson<Content>('/contents', { method: 'POST', body: JSON.stringify(input) });
}

export function patchContent(contentId: string, patch: Partial<Content>): Promise<Content> {
  if (USE_MOCK) return mocks.patchContent(contentId, patch);
  return fetchJson<Content>(`/contents/${contentId}`, { method: 'PATCH', body: JSON.stringify(patch) });
}

export function listTripContents(tripId: string): Promise<Content[]> {
  if (USE_MOCK) return mocks.listTripContents(tripId);
  return fetchJson<Content[]>(`/trips/${tripId}/contents`);
}
