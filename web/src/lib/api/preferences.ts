import type { GroupPreferences, UserPreferences } from '@/lib/types';
import { http, USE_MOCK } from './http';
import * as mocks from '@/lib/mocks';

export function getUserPreferences(userId: string): Promise<UserPreferences> {
  if (USE_MOCK) return mocks.getUserPreferences(userId);
  return http<UserPreferences>(`/users/${userId}/preferences`);
}

export function getGroupPreferences(groupId: string): Promise<GroupPreferences> {
  if (USE_MOCK) return mocks.getGroupPreferences(groupId);
  return http<GroupPreferences>(`/groups/${groupId}/preferences`);
}
