import type {
  Content,
  GroupPreferences,
  Itinerary,
  ItineraryRequest,
  Trip,
  UserPreferences,
} from '@/lib/types';
import { mockStore } from './store';

// 로딩 UI 확인용 지연 (500~1500ms)
const sleep = (min = 500, max = 1500) =>
  new Promise<void>((r) => setTimeout(r, min + Math.random() * (max - min)));

export async function createContent(input: {
  url: string;
  userId: string;
  tripId: string;
  note?: string;
}): Promise<Content> {
  await sleep();
  return mockStore.createContent(input);
}

export async function patchContent(contentId: string, patch: Partial<Content>): Promise<Content> {
  await sleep();
  return mockStore.patchContent(contentId, patch);
}

export async function listTripContents(tripId: string): Promise<Content[]> {
  await sleep();
  return mockStore.listTripContents(tripId);
}

export async function getUserPreferences(userId: string): Promise<UserPreferences> {
  await sleep();
  return mockStore.getUserPreferences(userId);
}

export async function createTrip(input: {
  name: string;
  destination: string;
  startDate: string;
  endDate: string;
  memberIds: string[];
}): Promise<Trip> {
  await sleep();
  return mockStore.createTrip(input);
}

export async function getTrip(tripId: string): Promise<Trip> {
  await sleep();
  return mockStore.getTrip(tripId);
}

export async function getGroupPreferences(groupId: string): Promise<GroupPreferences> {
  await sleep();
  return mockStore.getGroupPreferences(groupId);
}

export async function createItinerary(groupId: string, request: ItineraryRequest): Promise<Itinerary> {
  // 파이프라인(5-3)이 여러 단계를 거치는 걸 체감하도록 조금 더 길게 지연한다.
  await sleep(1000, 2000);
  return mockStore.createItinerary(groupId, request);
}

export async function getLatestItinerary(tripId: string): Promise<Itinerary | null> {
  await sleep();
  return mockStore.getLatestItinerary(tripId);
}
