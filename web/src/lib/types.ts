export type Category = 'cafe' | 'food' | 'exhibition' | 'shopping' | 'sightseeing' | 'activity';
export type TimeSlot = 'morning' | 'afternoon' | 'evening' | 'night';

export interface User { userId: string; name: string }

export interface Trip {
  tripId: string; name: string; destination: string;
  startDate: string; endDate: string;            // YYYY-MM-DD
  dayStartTime?: string; dayEndTime?: string;
  members: User[];
}

export interface PlaceInfo {
  name: string; address?: string; lat?: number; lng?: number;
  verified: boolean;                             // 장소 API로 실존 확인 여부
  openHours?: string;
}

export interface Content {                       // 숏폼 1건의 분석 결과
  contentId: string; tripId: string; userId: string;
  url: string; platform: 'instagram' | 'youtube' | 'tiktok' | 'other';
  place: PlaceInfo; category: Category; area: string;
  tags: string[];                                // 예: ['디저트','데이트','감성']
  activityType?: string; mood?: string; recommendedTime?: TimeSlot;
  confidence: number;                            // 0~1
  userEdited: boolean; savedAt: string;
}

export interface PreferenceItem {
  key: string; label: string; type: 'category' | 'tag';
  score: number;                                 // 원점수 (화면 노출 금지)
  normalized: number;                            // 0~100, 해당 유저 최고=100
  evidenceCount: number;
}
export interface UserPreferences { userId: string; top: PreferenceItem[]; all: PreferenceItem[] }

export interface GroupPreferences {
  members: { userId: string; name: string; top: PreferenceItem[] }[];
  common: { key: string; label: string; memberIds: string[] }[];                 // 2명 이상 공통
  unique: { userId: string; key: string; label: string; normalized: number }[];  // 개인 고유(강함)
  matrix: { userIds: string[]; keys: string[]; values: number[][] };             // values[user][key]
}

export interface ItineraryRequest {
  date?: string;
  area: string; startTime: string; endTime: string;  // 'HH:mm'
  budget?: number; includeMeals: boolean; mustVisitContentIds: string[];
}
export interface ItineraryItem {
  order: number; startTime: string; endTime: string;
  place: PlaceInfo; category: string; contentId?: string;
  placeId?: string; userScores?: Record<string, number>; groupScore?: number;
  reason: string;                                    // 추천 이유
  relatedUsers: { userId: string; preferenceKey: string; preferenceLabel: string }[];
}
export interface Itinerary {
  itineraryId: string; tripId: string;
  days: { day: number; date: string; items: ItineraryItem[] }[];
  reflection: { userId: string; name: string; reflectionPercent: number | null;
                coveredTop: number; totalTop: number }[];   // 서버 계산값
  allMembersCovered: boolean;                        // 모든 구성원 취향이 1회 이상 반영됐는가
  rebalanced: boolean;                               // 균형 보정 재생성 여부
  preferenceCoverage?: Record<string, number>;
  preferenceReflection?: Record<string, { matched_categories: string[]; total_categories: number; preference_reflection_percent: number | null }>;
  placeSource?: string; summary?: string; unverifiableConditions?: string[];
}
