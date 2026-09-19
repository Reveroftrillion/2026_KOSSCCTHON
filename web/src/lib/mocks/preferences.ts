import type { GroupPreferences, PreferenceItem } from '@/lib/types'
import { sleep } from '@/lib/api/http'
import { getTripMock } from './trips'

// SPEC 6장 시드 정규화 값(유저별 최고=100 기준). FE1의 C-03(숏폼 저장 → 취향 누적)이
// 실제 Content 저장소를 노출하면 이 고정 시드 대신 그 계산 결과를 사용하도록 교체한다.
const CATEGORY_SEED: Record<string, { cafe: number; exhibition: number; shopping: number }> = {
  u1: { cafe: 90, exhibition: 40, shopping: 20 }, // 원영
  u2: { cafe: 30, exhibition: 55, shopping: 95 }, // 민수
  u3: { cafe: 75, exhibition: 85, shopping: 35 }, // 지수
}

const CATEGORY_LABELS: Record<string, string> = {
  cafe: '카페',
  exhibition: '전시',
  shopping: '쇼핑',
}

const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS)

// 공통 취향으로 볼 기준선. 이 값 이상을 가진 멤버가 2명 이상이면 "공통"으로 표시한다.
const COMMON_THRESHOLD = 60
// 다른 멤버의 최고값보다 이만큼 이상 앞서면 그 멤버만의 "개인 고유" 취향으로 표시한다.
const UNIQUE_GAP = 30

function buildTop(userId: string): PreferenceItem[] {
  const seed = CATEGORY_SEED[userId]
  if (!seed) return []
  return CATEGORY_KEYS.map((key) => {
    const normalized = seed[key as keyof typeof seed]
    return {
      key,
      label: CATEGORY_LABELS[key],
      type: 'category' as const,
      score: 0, // 원점수는 화면에 노출하지 않는다 (SPEC 5-1)
      normalized,
      evidenceCount: Math.max(1, Math.round(normalized / 20)),
    }
  }).sort((a, b) => b.normalized - a.normalized)
}

export async function getGroupPreferencesMock(tripId: string): Promise<GroupPreferences> {
  await sleep(600 + Math.random() * 700)

  const trip = await getTripMock(tripId)
  const members = trip.members.map((u) => ({
    userId: u.userId,
    name: u.name,
    top: buildTop(u.userId),
  }))

  const matrix = {
    userIds: members.map((m) => m.userId),
    keys: CATEGORY_KEYS,
    values: members.map((m) => CATEGORY_KEYS.map((key) => m.top.find((p) => p.key === key)?.normalized ?? 0)),
  }

  const common: GroupPreferences['common'] = CATEGORY_KEYS.filter((key) => {
    const holders = members.filter((m) => (m.top.find((p) => p.key === key)?.normalized ?? 0) >= COMMON_THRESHOLD)
    return holders.length >= 2
  }).map((key) => ({
    key,
    label: CATEGORY_LABELS[key],
    memberIds: members
      .filter((m) => (m.top.find((p) => p.key === key)?.normalized ?? 0) >= COMMON_THRESHOLD)
      .map((m) => m.userId),
  }))

  const unique: GroupPreferences['unique'] = []
  for (const key of CATEGORY_KEYS) {
    const values = members.map((m) => m.top.find((p) => p.key === key)?.normalized ?? 0)
    const sorted = [...values].sort((a, b) => b - a)
    const [top1, top2 = 0] = sorted
    if (top1 < COMMON_THRESHOLD || top1 - top2 < UNIQUE_GAP) continue
    const ownerIndex = values.indexOf(top1)
    const owner = members[ownerIndex]
    unique.push({ userId: owner.userId, key, label: CATEGORY_LABELS[key], normalized: top1 })
  }

  return { members, common, unique, matrix }
}
