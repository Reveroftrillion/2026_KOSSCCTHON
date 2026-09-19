import type {
  GroupPreferences,
  PreferenceItem,
  UserPreferences,
} from '@/lib/types'

import {
  http,
  USE_MOCK,
} from './http'

import * as mocks from '@/lib/mocks'

import { getTrip } from './trips'
import { categoryLabel } from '@/lib/categories'


interface BackendPreferenceProfile {
  user_id: string
  category_preferences: Record<string, number>
  keyword_preferences: Record<string, number>
}


const STRONG_PREFERENCE_THRESHOLD = 50


function buildUserPreferences(
  profile: BackendPreferenceProfile,
): UserPreferences {
  const rawItems: Array<{
    key: string
    label: string
    type: 'category' | 'tag'
    score: number
  }> = []

  for (
    const [key, score]
    of Object.entries(
      profile.category_preferences ?? {},
    )
  ) {
    if (
      typeof score !== 'number' ||
      !Number.isFinite(score) ||
      score <= 0
    ) {
      continue
    }

    rawItems.push({
      key,
      label: categoryLabel(key),
      type: 'category',
      score,
    })
  }

  for (
    const [key, score]
    of Object.entries(
      profile.keyword_preferences ?? {},
    )
  ) {
    if (
      typeof score !== 'number' ||
      !Number.isFinite(score) ||
      score <= 0
    ) {
      continue
    }

    /*
     * category와 keyword가 같은 문자열일 수 있으므로
     * 내부 key만 tag: prefix로 구분한다.
     *
     * 화면에는 label만 보여준다.
     */
    rawItems.push({
      key: `tag:${key}`,
      label: key,
      type: 'tag',
      score,
    })
  }

  const maxScore =
    rawItems.reduce(
      (max, item) =>
        Math.max(max, item.score),
      0,
    ) || 1

  const all: PreferenceItem[] =
    rawItems
      .map((item) => ({
        key: item.key,
        label: item.label,
        type: item.type,
        score: item.score,

        normalized:
          Math.round(
            (item.score / maxScore) * 100,
          ),

        /*
         * 현재 Backend preference API는
         * 근거 콘텐츠 개수를 별도로 반환하지 않는다.
         */
        evidenceCount: 0,
      }))
      .sort(
        (a, b) =>
          b.normalized - a.normalized,
      )

  return {
    userId: profile.user_id,
    top: all.slice(0, 5),
    all,
  }
}


export async function getUserPreferences(
  userId: string,
): Promise<UserPreferences> {
  if (USE_MOCK) {
    return mocks.getUserPreferences(
      userId,
    )
  }

  const profile =
    await http<BackendPreferenceProfile>(
      `/api/users/${encodeURIComponent(userId)}/preferences`,
    )

  return buildUserPreferences(
    profile,
  )
}


export async function getGroupPreferences(
  tripId: string,
): Promise<GroupPreferences> {
  if (USE_MOCK) {
    return mocks.getGroupPreferences(
      tripId,
    )
  }

  const encodedTripId =
    encodeURIComponent(
      tripId,
    )

  /*
   * Backend의 실제 Group Preference API는
   * 여행 멤버별 profile 배열을 반환한다.
   *
   * 멤버 이름은 Trip API에서 함께 가져온다.
   */
  const [
    trip,
    profiles,
  ] = await Promise.all([
    getTrip(tripId),

    http<
      BackendPreferenceProfile[]
    >(
      `/api/trips/${encodedTripId}/preferences`,
    ),
  ])

  const profileByUserId =
    new Map(
      profiles.map(
        (profile) => [
          profile.user_id,
          profile,
        ],
      ),
    )

  /*
   * 콘텐츠가 아직 없는 멤버도
   * 그룹 취향 화면에 포함한다.
   */
  const memberPreferences =
    trip.members.map(
      (member) => {
        const profile =
          profileByUserId.get(
            member.userId,
          ) ?? {
            user_id:
              member.userId,

            category_preferences:
              {},

            keyword_preferences:
              {},
          }

        return {
          userId:
            member.userId,

          name:
            member.name,

          preferences:
            buildUserPreferences(
              profile,
            ),
        }
      },
    )


  const members:
    GroupPreferences['members'] =
    memberPreferences.map(
      ({
        userId,
        name,
        preferences,
      }) => ({
        userId,
        name,
        top:
          preferences.top,
      }),
    )


  /*
   * 모든 멤버의 preference를 key 기준으로 묶는다.
   */
  const byKey =
    new Map<
      string,
      {
        label: string
        entries: {
          userId: string
          normalized: number
        }[]
      }
    >()

  for (
    const member
    of memberPreferences
  ) {
    for (
      const item
      of member.preferences.all
    ) {
      const bucket =
        byKey.get(
          item.key,
        ) ?? {
          label: item.label,
          entries: [],
        }

      bucket.entries.push({
        userId:
          member.userId,

        normalized:
          item.normalized,
      })

      byKey.set(
        item.key,
        bucket,
      )
    }
  }


  const common:
    GroupPreferences['common'] =
    []

  const unique:
    GroupPreferences['unique'] =
    []


  for (
    const [
      key,
      {
        label,
        entries,
      },
    ]
    of byKey
  ) {
    const strong =
      entries.filter(
        (entry) =>
          entry.normalized >=
          STRONG_PREFERENCE_THRESHOLD,
      )

    if (
      strong.length >= 2
    ) {
      common.push({
        key,
        label,

        memberIds:
          strong.map(
            (entry) =>
              entry.userId,
          ),
      })
    } else if (
      strong.length === 1
    ) {
      unique.push({
        userId:
          strong[0].userId,

        key,
        label,

        normalized:
          strong[0].normalized,
      })
    }
  }


  /*
   * Matrix에는 현재 그룹에서 실제 등장한
   * category와 keyword를 모두 표시한다.
   *
   * 가장 높은 preference가 위쪽에 오도록 정렬한다.
   */
  const matrixKeys =
    [...byKey.keys()]
      .sort(
        (a, b) => {
          const maxA =
            Math.max(
              ...memberPreferences.map(
                (member) =>
                  member.preferences.all
                    .find(
                      (item) =>
                        item.key === a,
                    )
                    ?.normalized ?? 0,
              ),
            )

          const maxB =
            Math.max(
              ...memberPreferences.map(
                (member) =>
                  member.preferences.all
                    .find(
                      (item) =>
                        item.key === b,
                    )
                    ?.normalized ?? 0,
              ),
            )

          if (
            maxA !== maxB
          ) {
            return maxB - maxA
          }

          return a.localeCompare(
            b,
          )
        },
      )


  const values =
    memberPreferences.map(
      (member) =>
        matrixKeys.map(
          (key) =>
            member.preferences.all
              .find(
                (item) =>
                  item.key === key,
              )
              ?.normalized ?? 0,
        ),
    )


  return {
    members,
    common,
    unique,

    matrix: {
      userIds:
        trip.members.map(
          (member) =>
            member.userId,
        ),

      keys:
        matrixKeys,

      values,
    },
  }
}