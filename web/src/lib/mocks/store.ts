import { CATEGORY_LABEL, CATEGORY_LIST } from '@/lib/constants';
import type {
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
    const tripContents = this.listTripContents(tripId);
    const mustVisit = tripContents.filter((c) => request.mustVisitContentIds.includes(c.contentId));
    const rest = tripContents.filter((c) => !request.mustVisitContentIds.includes(c.contentId));
    const ordered = [...mustVisit, ...rest].slice(0, Math.max(mustVisit.length, 4));

    const items: ItineraryItem[] = ordered.map((content, i) => {
      const label = CATEGORY_LABEL[content.category];
      const memberName = trip.members.find((m) => m.userId === content.userId)?.name ?? '멤버';
      return {
        order: i + 1,
        startTime: addMinutes(request.startTime, i * 90),
        endTime: addMinutes(request.startTime, i * 90 + 75),
        place: content.place,
        category: content.category,
        contentId: content.contentId,
        reason: `${memberName}님이 저장한 ${label} 취향을 반영했어요.`,
        relatedUsers: [{ userId: content.userId, preferenceKey: content.category, preferenceLabel: label }],
      };
    });

    const reflection = trip.members.map((member) => {
      const prefs = this.buildUserPreferences(member.userId);
      const topKeys = new Set(prefs.top.map((p) => p.key));
      const coveredKeys = new Set(items.map((item) => item.category).filter((key) => topKeys.has(key)));
      const totalTop = prefs.top.length || 1;
      return {
        userId: member.userId,
        name: member.name,
        coveredTop: coveredKeys.size,
        totalTop,
        reflectionPercent: Math.round((coveredKeys.size / totalTop) * 100),
      };
    });

    const itinerary: Itinerary = {
      itineraryId: `itin-${tripId}-${Date.now()}`,
      tripId,
      days: [{ day: 1, date: trip.startDate, items }],
      reflection,
      allMembersCovered: reflection.every((r) => r.coveredTop > 0),
      rebalanced: false,
    };
    this.itineraries.set(tripId, itinerary);
    return itinerary;
  }

  getLatestItinerary(tripId: string): Itinerary {
    const itinerary = this.itineraries.get(tripId);
    if (!itinerary) throw new Error(`Itinerary not found for trip: ${tripId}`);
    return itinerary;
  }
}

export const mockStore = new MockStore();
