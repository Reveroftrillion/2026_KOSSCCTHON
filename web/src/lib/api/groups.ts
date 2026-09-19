import type { GroupPreferences } from '@/lib/types'
import { getGroupPreferencesMock } from '@/lib/mocks/preferences'
import { http, USE_MOCK } from './http'

// GET /groups/{id}/preferences (group_id == trip_id, SPEC 5-2)
export function getGroupPreferences(tripId: string): Promise<GroupPreferences> {
  if (USE_MOCK) return getGroupPreferencesMock(tripId)
  return http<GroupPreferences>(`/groups/${encodeURIComponent(tripId)}/preferences`)
}
