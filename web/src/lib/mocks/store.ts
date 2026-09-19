import { CATEGORY_LABEL, CATEGORY_LIST } from '@/lib/constants';
import type {
  Category,
  Content,
  GroupPreferences,
  Itinerary,
  ItineraryItem,
  ItineraryRequest,
  PreferenceItem,
  Trip,
  User,
  UserPreferences,
} from '@/lib/types';
import { analyzeUrl } from './analyze';
import {
  DEMO_USERS,
  INITIAL_CATEGORY_SCORES,
  SEED_TRIP_ID,
  seedContents,
  seedItinerary,
  seedTrip,
} from './seed';

interface PreferenceEntry {
  key: string;
  label: string;
  type: 'category' | 'tag';
  score: number;
  evidenceCount: number;
}

// 5-3 서버 규칙: 주 카테고리 +3, 세부 태그 +1, 직접 관심 +2, AI 분석 확인 +1.
const SCORE_DELTA = { MAIN_CATEGORY: 3, TAG: 1, DIRECT_INTEREST: 2, AI_CONFIRM: 1 } as const;
// GroupPreferences 매트릭스/공통·고유 판정 기준: 정규화 값이 이 이상이면 "선호한다"로 본다.
const STRONG_PREFERENCE_THRESHOLD = 50;

function addMinutes(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number);
  const total = h * 60 + m + minutes;
  const hh = Math.floor((((total % (24 * 60)) + 24 * 60) % (24 * 60)) / 60)
    .toString()
    .padStart(2, '0');
  const mm = (((total % 60) + 60) % 60).toString().padStart(2, '0');
  return `${hh}:${mm}`;
}

// SPEC 6장 시드: 성수동 실제 좌표, 카페 2곳·전시 1곳·쇼핑 1곳 이상, 모든 유저 반영도 1개 이상.
const SEED_PLACES: Array<{
  name: string;
  address: string;
  lat: number;
  lng: number;
  category: Category;
  durationMinutes: number;
  reasonTemplate: (names: string[]) => string;
  users: (memberIds: string[]) => string[]; // 참여 유저 id, 실제 멤버가 있을 때만 반영
}> = [
  {
    name: '성수 팝업스토어',
    address: '서울 성동구 아차산로 1길',
    lat: 37.5445,
    lng: 127.0559,
    category: 'shopping',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 팝업 및 쇼핑 취향을 반영했습니다.`,
    users: (ids) => ids.slice(1, 2), // 민수(두 번째 멤버) 취향
  },
  {
    name: '성수 전시회',
    address: '서울 성동구 연무장길',
    lat: 37.5443,
    lng: 127.0567,
    category: 'exhibition',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 전시 취향을 반영했습니다.`,
    users: (ids) => ids.slice(2, 3).concat(ids.slice(0, 1)), // 지수 + 원영
  },
  {
    name: '성수 브런치 카페',
    address: '서울 성동구 성수이로',
    lat: 37.5447,
    lng: 127.0578,
    category: 'cafe',
    durationMinutes: 75,
    reasonTemplate: (names) => `${names.join(', ')}의 카페 취향을 반영했습니다.`,
    users: (ids) => ids.slice(0, 1), // 원영
  },
  {
    name: '성수 디저트 카페',
    address: '서울 성동구 서울숲2길',
    lat: 37.5466,
    lng: 127.0453,
    category: 'cafe',
    durationMinutes: 75,
    reasonTemplate: (names) => `${names.join(', ')}의 카페 취향을 반영했습니다.`,
    users: (ids) => ids.slice(2, 3), // 지수
  },
  {
    name: '성수 일식집',
    address: '서울 성동구 왕십리로',
    lat: 37.5417,
    lng: 127.0558,
    category: 'food',
    durationMinutes: 90,
    reasonTemplate: (names) => `${names.join(', ')}의 음식 취향을 반영했고, 그룹의 저녁 식사 조건을 충족했습니다.`,
    users: (ids) => ids.slice(0, 1), // 원영
  },
];

class MockStore {
  private trips = new Map<string, Trip>();
  private contents: Content[] = [];
  private preferences = new Map<string, Map<string, PreferenceEntry>>();
  private itineraries = new Map<string, Itinerary>();
  private contentSeq = 1;
  private tripSeq = 1;

  constructor() {
    this.reset();
  }

  reset() {
    this.trips = new Map([[seedTrip.tripId, seedTrip]]);
    this.contents = seedContents.map((c) => ({ ...c }));
    this.contentSeq = seedContents.length + 1;
    this.tripSeq = 2;

    this.preferences = new Map(DEMO_USERS.map((u) => [u.userId, new Map<string, PreferenceEntry>()]));
    for (const { userId, category, score } of INITIAL_CATEGORY_SCORES) {
      this.bumpScore(userId, category, CATEGORY_LABEL[category], 'category', score, 1);
    }

    this.itineraries = new Map([[SEED_TRIP_ID, seedItinerary]]);
  }

  private bumpScore(
    userId: string,
    key: string,
    label: string,
    type: 'category' | 'tag',
    delta: number,
    evidenceDelta = 1
  ) {
    const userMap = this.preferences.get(userId);
    if (!userMap) return;
    const existing = userMap.get(key);
    if (existing) {
      existing.score += delta;
      existing.evidenceCount += evidenceDelta;
    } else {
      userMap.set(key, { key, label, type, score: delta, evidenceCount: evidenceDelta });
    }
  }

  // 정규화: 해당 유저의 최고 원점수 = 100 (6장 규칙). 원점수(score)는 반환은 하되 화면 노출은 금지.
  private buildUserPreferences(userId: string): UserPreferences {
    const userMap = this.preferences.get(userId);
    const entries = userMap ? [...userMap.values()] : [];
    const max = entries.reduce((m, e) => Math.max(m, e.score), 0) || 1;
    const all: PreferenceItem[] = entries
      .map((e) => ({
        key: e.key,
        label: e.label,
        type: e.type,
        score: e.score,
        normalized: Math.round((e.score / max) * 100),
        evidenceCount: e.evidenceCount,
      }))
      .sort((a, b) => b.normalized - a.normalized);
    return { userId, top: all.slice(0, 5), all };
  }

  // ---- Trips ----
  getTrip(tripId: string): Trip {
    const trip = this.trips.get(tripId);
    if (!trip) throw new Error(`Trip not found: ${tripId}`);
    return trip;
  }

  createTrip(input: {
    name: string;
    destination: string;
    startDate: string;
    endDate: string;
    memberIds: string[];
  }): Trip {
    const members: User[] = input.memberIds
      .map((id) => DEMO_USERS.find((u) => u.userId === id))
      .filter((u): u is User => Boolean(u));
    const trip: Trip = {
      tripId: `trip${this.tripSeq++}`,
      name: input.name,
      destination: input.destination,
      startDate: input.startDate,
      endDate: input.endDate,
      members,
    };
    this.trips.set(trip.tripId, trip);
    return trip;
  }

  // ---- Contents ----
  listTripContents(tripId: string): Content[] {
    return this.contents.filter((c) => c.tripId === tripId);
  }

  createContent(input: { url: string; userId: string; tripId: string; note?: string }): Content {
    const analyzed = analyzeUrl(input.url, input.note);
    const content: Content = {
      contentId: `c${this.contentSeq++}`,
      tripId: input.tripId,
      userId: input.userId,
      url: input.url,
      platform: analyzed.platform,
      place: analyzed.place,
      category: analyzed.category,
      area: analyzed.area,
      tags: analyzed.tags,
      activityType: analyzed.activityType,
      mood: analyzed.mood,
      recommendedTime: analyzed.recommendedTime,
      confidence: analyzed.confidence,
      userEdited: false,
      savedAt: new Date().toISOString(),
    };
    this.contents.push(content);
    this.bumpScore(content.userId, content.category, CATEGORY_LABEL[content.category], 'category', SCORE_DELTA.MAIN_CATEGORY, 1);
    for (const tag of content.tags) {
      this.bumpScore(content.userId, tag, tag, 'tag', SCORE_DELTA.TAG, 1);
    }
    return content;
  }

  patchContent(contentId: string, patch: Partial<Content>): Content {
    const index = this.contents.findIndex((c) => c.contentId === contentId);
    if (index === -1) throw new Error(`Content not found: ${contentId}`);
    const updated: Content = { ...this.contents[index], ...patch, contentId, userEdited: true };
    this.contents[index] = updated;
    // 사용자가 확인·수정 후 저장 = "AI 분석 확인" 반영으로 간주.
    this.bumpScore(updated.userId, updated.category, CATEGORY_LABEL[updated.category], 'category', SCORE_DELTA.AI_CONFIRM, 1);
    for (const tag of updated.tags) {
      this.bumpScore(updated.userId, tag, tag, 'tag', SCORE_DELTA.AI_CONFIRM, 1);
    }
    return updated;
  }

  // ---- Preferences ----
  getUserPreferences(userId: string): UserPreferences {
    return this.buildUserPreferences(userId);
  }

  getGroupPreferences(tripId: string): GroupPreferences {
    const trip = this.getTrip(tripId);
    const memberPrefs = trip.members.map((member) => ({
      userId: member.userId,
      name: member.name,
      prefs: this.buildUserPreferences(member.userId),
    }));

    const members = memberPrefs.map(({ userId, name, prefs }) => ({ userId, name, top: prefs.top }));

    const byKey = new Map<string, { label: string; entries: { userId: string; normalized: number }[] }>();
    for (const { userId, prefs } of memberPrefs) {
      for (const item of prefs.all) {
        const bucket = byKey.get(item.key) ?? { label: item.label, entries: [] };
        bucket.entries.push({ userId, normalized: item.normalized });
        byKey.set(item.key, bucket);
      }
    }

    const common: GroupPreferences['common'] = [];
    const unique: GroupPreferences['unique'] = [];
    for (const [key, { label, entries }] of byKey) {
      const strong = entries.filter((e) => e.normalized >= STRONG_PREFERENCE_THRESHOLD);
      if (strong.length >= 2) {
        common.push({ key, label, memberIds: strong.map((e) => e.userId) });
      } else if (strong.length === 1) {
        unique.push({ userId: strong[0].userId, key, label, normalized: strong[0].normalized });
      }
    }

    const values = memberPrefs.map(({ prefs }) =>
      CATEGORY_LIST.map((key) => prefs.all.find((item) => item.key === key)?.normalized ?? 0)
    );

    return {
      members,
      common,
      unique,
      matrix: { userIds: trip.members.map((m) => m.userId), keys: [...CATEGORY_LIST], values },
    };
  }

  // ---- Itinerary ----
  createItinerary(tripId: string, request: ItineraryRequest): Itinerary {
    const trip = this.getTrip(tripId);
    const memberIds = trip.members.map((m) => m.userId);
    const nameById = new Map(trip.members.map((m) => [m.userId, m.name]));
    const contents = this.listTripContents(tripId);

    const basePlaces = request.includeMeals ? SEED_PLACES : SEED_PLACES.filter((p) => p.category !== 'food');

    let cursor = request.startTime || '13:00';
    const seedItems: ItineraryItem[] = basePlaces.map((place, index) => {
      const startTime = cursor;
      const endTime = addMinutes(startTime, place.durationMinutes);
      cursor = endTime;
      const userIds = place.users(memberIds).filter((id): id is string => Boolean(id) && memberIds.includes(id));
      const names = userIds.map((id) => nameById.get(id) ?? id);
      return {
        order: index + 1,
        startTime,
        endTime,
        place: { name: place.name, address: place.address, lat: place.lat, lng: place.lng, verified: true },
        category: place.category,
        reason: place.reasonTemplate(names),
        relatedUsers: userIds.map((id) => ({
          userId: id,
          preferenceKey: place.category,
          preferenceLabel: CATEGORY_LABEL[place.category],
        })),
      };
    });

    // 사용자가 장바구니에서 고른 필수 장소를 마지막에 덧붙인다.
    const mustVisitItems: ItineraryItem[] = request.mustVisitContentIds
      .map((contentId) => contents.find((c) => c.contentId === contentId))
      .filter((c): c is NonNullable<typeof c> => Boolean(c))
      .map((content, i) => {
        const startTime = cursor;
        const endTime = addMinutes(startTime, 60);
        cursor = endTime;
        const ownerName = nameById.get(content.userId) ?? content.userId;
        return {
          order: seedItems.length + i + 1,
          startTime,
          endTime,
          place: content.place,
          category: content.category,
          contentId: content.contentId,
          reason: `${ownerName}님이 저장한 장소를 필수 코스로 포함했습니다.`,
          relatedUsers: [
            {
              userId: content.userId,
              preferenceKey: content.category,
              preferenceLabel: CATEGORY_LABEL[content.category],
            },
          ],
        } satisfies ItineraryItem;
      });

    const items = [...seedItems, ...mustVisitItems];

    // 반영도는 "서버"가 계산한다(SPEC 5-3). 프론트 컴포넌트는 이 값을 그대로 표시만 한다.
    const reflection = trip.members.map((member) => {
      const top = this.buildUserPreferences(member.userId).top;
      const coveredKeys = new Set<string>(
        items.filter((item) => item.relatedUsers.some((u) => u.userId === member.userId)).map((item) => item.category)
      );
      const coveredTop = top.filter((p) => coveredKeys.has(p.key)).length;
      const totalTop = top.length || 1;
      return {
        userId: member.userId,
        name: member.name,
        reflectionPercent: Math.round((coveredTop / totalTop) * 100),
        coveredTop,
        totalTop,
      };
    });

    const allMembersCovered = trip.members.every((member) =>
      items.some((item) => item.relatedUsers.some((u) => u.userId === member.userId))
    );

    const itinerary: Itinerary = {
      itineraryId: `itin-${tripId}-${Date.now()}`,
      tripId,
      days: [{ day: 1, date: trip.startDate, items }],
      reflection,
      allMembersCovered,
      rebalanced: false,
    };
    this.itineraries.set(tripId, itinerary);
    return itinerary;
  }

  getLatestItinerary(tripId: string): Itinerary | null {
    return this.itineraries.get(tripId) ?? null;
  }
}

export const mockStore = new MockStore();
