import type { Trip, User } from '@/lib/types'
import { sleep } from '@/lib/api/http'

// 명세 6장 시드 유저. FE1의 공통 시드(C-03)가 생기면 그쪽을 import하도록 교체한다.
export const DEMO_USERS: User[] = [
  { userId: 'u1', name: '원영' },
  { userId: 'u2', name: '민수' },
  { userId: 'u3', name: '지수' },
]

export interface CreateTripInput {
  name: string
  destination: string
  startDate: string
  endDate: string
  memberIds: string[]
}

const STORAGE_KEY = 'tripclip:mock:trips'
const memory = new Map<string, Trip>()

// 새로고침해도 방이 남도록 localStorage에도 저장한다 (mock 전용).
function load(): Map<string, Trip> {
  if (memory.size === 0 && typeof window !== 'undefined') {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (raw) {
        for (const t of JSON.parse(raw) as Trip[]) memory.set(t.tripId, t)
      }
    } catch {
      // 저장값이 깨졌으면 무시하고 빈 상태로 시작
    }
  }
  return memory
}

function persist() {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...memory.values()]))
  } catch {
    // 저장 실패는 데모 동작에 영향 없음
  }
}

export async function createTripMock(input: CreateTripInput): Promise<Trip> {
  await sleep(500 + Math.random() * 700)
  const store = load()
  const members = DEMO_USERS.filter((u) => input.memberIds.includes(u.userId))
  const trip: Trip = {
    tripId: `t${Date.now().toString(36)}`,
    name: input.name,
    destination: input.destination,
    startDate: input.startDate,
    endDate: input.endDate,
    members,
  }
  store.set(trip.tripId, trip)
  persist()
  return trip
}

export async function getTripMock(tripId: string): Promise<Trip> {
  await sleep(300 + Math.random() * 400)
  const trip = load().get(tripId)
  if (!trip) throw new Error('여행방을 찾을 수 없어요.')
  return trip
}
