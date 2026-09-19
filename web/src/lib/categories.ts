import type { Category } from '@/lib/types'

// 카테고리 키 → 화면에 보여줄 한글 라벨. (공통 파일: 항목 추가만 허용)
export const CATEGORY_LABELS: Record<Category, string> = {
  cafe: '카페',
  food: '음식',
  exhibition: '전시',
  shopping: '쇼핑',
  sightseeing: '관광',
  activity: '액티비티',
}

export function categoryLabel(category: string): string {
  return (CATEGORY_LABELS as Record<string, string>)[category] ?? category
}
