import type { Category, TimeSlot } from '@/lib/types';

export const CATEGORY_LABEL: Record<Category, string> = {
  cafe: '카페',
  food: '맛집',
  exhibition: '전시',
  shopping: '쇼핑',
  sightseeing: '관광',
  activity: '액티비티',
};

export const CATEGORY_LIST = Object.keys(CATEGORY_LABEL) as Category[];

export const TIME_SLOT_LABEL: Record<TimeSlot, string> = {
  morning: '아침',
  afternoon: '오후',
  evening: '저녁',
  night: '밤',
};

export const TIME_SLOT_LIST = Object.keys(TIME_SLOT_LABEL) as TimeSlot[];
