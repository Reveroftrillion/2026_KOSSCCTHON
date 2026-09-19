import type { GroupPreferences, UserPreferences } from '@/lib/types';
import { USE_MOCK } from './config';
import { fetchJson } from './http';
import * as mocks from '@/lib/mocks';

export function getUserPreferences(userId: string): Promise<UserPreferences> {
  if (USE_MOCK) return mocks.getUserPreferences(userId);
  return fetchJson<UserPreferences>(`/users/${userId}/preferences`);
}

export function getGroupPreferences(groupId: string): Promise<GroupPreferences> {
  if (USE_MOCK) return mocks.getGroupPreferences(groupId);
  return fetchJson<GroupPreferences>(`/groups/${groupId}/preferences`);
}
