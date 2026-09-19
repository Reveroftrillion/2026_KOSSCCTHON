import type { Trip } from '@/lib/types'
import { http, USE_MOCK } from './http'
import * as mocks from '@/lib/mocks'

interface CreateTripResponse {
  status: string
  message: string
  trip_id: string
  trip_name: string
  region: string
  start_date: string
  end_date: string
}

interface TripDetailResponse {
  status: string
  data: {
    trip_id: string
    owner_user_id: string
    trip_name: string
    region: string
    start_date: string
    end_date: string
    day_start_time: string
    day_end_time: string
    status: string
    description: string
  }
}

interface MembersResponse {
  status: string
  data: {
    user_id: string
    name: string
    joined_at: string
  }[]
}

export interface CreateTripInput {
  name: string
  destination: string
  startDate: string
  endDate: string
  memberIds: string[]
  ownerUserId: string
}

export async function createTrip(
  input: CreateTripInput,
): Promise<Trip> {
  if (USE_MOCK) {
    return mocks.createTrip({
      name: input.name,
      destination: input.destination,
      startDate: input.startDate,
      endDate: input.endDate,
      memberIds: input.memberIds,
    })
  }

  const created = await http<CreateTripResponse>(
    '/api/trips',
    {
      method: 'POST',
      body: JSON.stringify({
        trip_name: input.name,
        region: input.destination,
        start_date: input.startDate,
        end_date: input.endDate,
        owner_user_id: input.ownerUserId,
        day_start_time: '13:00:00',
        day_end_time: '20:00:00',
        description: '',
      }),
    },
  )

  const memberIds = Array.from(
    new Set([
      input.ownerUserId,
      ...input.memberIds,
    ]),
  )

  const additionalMembers = memberIds.filter(
    (userId) => userId !== input.ownerUserId,
  )

  await Promise.all(
    additionalMembers.map((userId) =>
      http(
        `/api/trips/${encodeURIComponent(created.trip_id)}/members`,
        {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
          }),
        },
      ),
    ),
  )

  return getTrip(created.trip_id)
}

export async function getTrip(
  tripId: string,
): Promise<Trip> {
  if (USE_MOCK) {
    return mocks.getTrip(tripId)
  }

  const encodedTripId = encodeURIComponent(tripId)

  const [tripResponse, membersResponse] =
    await Promise.all([
      http<TripDetailResponse>(
        `/api/trips/${encodedTripId}`,
      ),

      http<MembersResponse>(
        `/api/trips/${encodedTripId}/members`,
      ),
    ])

  const trip = tripResponse.data

  return {
    tripId: trip.trip_id,
    name: trip.trip_name,
    destination: trip.region,
    startDate: trip.start_date,
    endDate: trip.end_date,
    members: membersResponse.data.map(
      (member) => ({
        userId: member.user_id,
        name: member.name,
      }),
    ),
  }
}