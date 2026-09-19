'use client';

import { createContext, useContext, useMemo, useSyncExternalStore, type ReactNode } from 'react';
import type { User } from '@/lib/types';
import { DEMO_USERS } from '@/lib/mocks/seed';

const STORAGE_KEY = 'tripclip:current-user-id';

function isValidUserId(id: string | null): id is string {
  return !!id && DEMO_USERS.some((u) => u.userId === id);
}

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback);
  return () => window.removeEventListener('storage', callback);
}

function getSnapshot(): string {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isValidUserId(stored) ? stored : DEMO_USERS[0].userId;
  } catch {
    return DEMO_USERS[0].userId;
  }
}

function getServerSnapshot(): string {
  return DEMO_USERS[0].userId;
}

interface UserContextValue {
  currentUser: User;
  users: User[];
  setCurrentUserId: (userId: string) => void;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  // localStorage를 외부 스토어로 취급해 구독한다 (setState-in-effect 없이 SSR도 안전하게 처리).
  const currentUserId = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setCurrentUserId = (userId: string) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, userId);
    } catch {
      // 저장 실패는 무시 — 현재 세션 동안만 상태 유지
    }
    // 네이티브 storage 이벤트는 다른 탭에서만 발생하므로, 같은 탭에서도 즉시 반영되도록 수동 발행한다.
    window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY }));
  };

  const value = useMemo<UserContextValue>(
    () => ({
      currentUser: DEMO_USERS.find((u) => u.userId === currentUserId) ?? DEMO_USERS[0],
      users: DEMO_USERS,
      setCurrentUserId,
    }),
    [currentUserId]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error('useUser must be used within a UserProvider');
  return ctx;
}
