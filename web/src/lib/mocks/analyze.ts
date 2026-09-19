import type { Category, PlaceInfo, TimeSlot } from '@/lib/types';

const PLATFORM_PATTERNS: [RegExp, 'instagram' | 'youtube' | 'tiktok'][] = [
  [/instagram\.com/i, 'instagram'],
  [/(youtube\.com|youtu\.be)/i, 'youtube'],
  [/tiktok\.com/i, 'tiktok'],
];

const CATEGORY_KEYWORDS: [Category, RegExp][] = [
  ['cafe', /카페|디저트|커피|베이커리|빵집/],
  ['food', /맛집|식당|음식|밥집|레스토랑/],
  ['exhibition', /전시|미술관|갤러리|팝업/],
  ['shopping', /쇼핑|편집샵|스토어|매장/],
  ['sightseeing', /관광|명소|뷰맛집|야경|산책/],
  ['activity', /액티비티|체험|클래스|원데이/],
];

const TIME_KEYWORDS: [TimeSlot, RegExp][] = [
  ['morning', /아침|모닝|오전/],
  ['afternoon', /오후|점심|낮/],
  ['evening', /저녁|해질녘|노을/],
  ['night', /밤|야경|심야/],
];

function detectPlatform(url: string): 'instagram' | 'youtube' | 'tiktok' | 'other' {
  for (const [pattern, platform] of PLATFORM_PATTERNS) {
    if (pattern.test(url)) return platform;
  }
  return 'other';
}

function detectCategory(note: string): Category {
  for (const [category, pattern] of CATEGORY_KEYWORDS) {
    if (pattern.test(note)) return category;
  }
  return 'cafe';
}

function detectTimeSlot(note: string): TimeSlot {
  for (const [slot, pattern] of TIME_KEYWORDS) {
    if (pattern.test(note)) return slot;
  }
  return 'afternoon';
}

function extractHashtags(note: string): string[] {
  const matches = note.match(/#([\p{L}\p{N}_]+)/gu) ?? [];
  return [...new Set(matches.map((tag) => tag.slice(1)))].slice(0, 5);
}

function extractPlaceName(note: string): string | undefined {
  const withoutHashtags = note.replace(/#[\p{L}\p{N}_]+/gu, '').trim();
  const firstLine = withoutHashtags.split(/[\n.!?]/)[0]?.trim();
  return firstLine ? firstLine.slice(0, 30) : undefined;
}

export interface AnalyzedContent {
  platform: 'instagram' | 'youtube' | 'tiktok' | 'other';
  place: PlaceInfo;
  category: Category;
  area: string;
  tags: string[];
  activityType?: string;
  mood?: string;
  recommendedTime: TimeSlot;
  confidence: number;
}

// 실제 AI 분석을 흉내내는 목(mock) 휴리스틱.
// note(보정 입력)에서 키워드·해시태그를 뽑아 장소/카테고리/태그를 추정한다.
export function analyzeUrl(url: string, note?: string): AnalyzedContent {
  const trimmedNote = note?.trim() ?? '';
  const placeName = extractPlaceName(trimmedNote);

  return {
    platform: detectPlatform(url),
    place: {
      name: placeName ?? '이름 미확인 장소',
      verified: Boolean(placeName),
    },
    category: detectCategory(trimmedNote),
    area: '성수',
    tags: extractHashtags(trimmedNote),
    recommendedTime: detectTimeSlot(trimmedNote),
    confidence: trimmedNote ? 0.85 : 0.55,
  };
}
