import type { Category } from '@/lib/types';

export const CATEGORY_LIST: Category[] = [
  'cafe',
  'food',
  'exhibition',
  'shopping',
  'sightseeing',
  'activity',
];

export const CATEGORY_LABEL: Record<Category, string> = {
  cafe: '카페',
  food: '맛집',
  exhibition: '전시',
  shopping: '쇼핑',
  sightseeing: '관광',
  activity: '액티비티',
};
