import { sleep } from '@/lib/api/http'
import type { Category, Content } from '@/lib/types'

// 임시 fixture. FE1의 `GET /trips/{tripId}/contents`(lib/api)가 나오면
// 이 파일을 지우고 import 한 줄만 그쪽 함수로 바꾼다.
function make(
  n: number,
  tripId: string,
  userId: string,
  name: string,
  category: Category,
  tags: string[],
): Content {
  return {
    contentId: `tmp-${userId}-${n}`,
    tripId,
    userId,
    url: `https://www.instagram.com/reel/tmp${n}/`,
    platform: 'instagram',
    place: { name, verified: true },
    category,
    area: '성수',
    tags,
    confidence: 0.9,
    userEdited: false,
    savedAt: '2026-09-19T00:00:00.000Z',
  }
}

export async function getTripContents(tripId: string): Promise<Content[]> {
  await sleep(400)
  return [
    make(1, tripId, 'u1', '성수 디저트 카페', 'cafe', ['디저트', '감성']),
    make(2, tripId, 'u1', '성수 브런치 카페', 'cafe', ['브런치']),
    make(3, tripId, 'u2', '성수 편집숍', 'shopping', ['쇼핑']),
    // u3(지수)는 일부러 0건: "아직 저장이 없는 멤버" 안내 확인용
  ]
}
