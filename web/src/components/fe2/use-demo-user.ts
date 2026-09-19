'use client'

import { useSyncExternalStore } from 'react'

// 임시 데모 유저 선택 저장소. FE1의 user-context(C-04)가 나오면 그쪽으로 교체한다.
const KEY = 'tripclip:demoUserId'
const listeners = new Set<() => void>()

function subscribe(callback: () => void) {
  listeners.add(callback)
  window.addEventListener('storage', callback)
  return () => {
    listeners.delete(callback)
    window.removeEventListener('storage', callback)
  }
}

function getSnapshot(): string | null {
  try {
    return window.localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function useDemoUserId(): string | null {
  return useSyncExternalStore(subscribe, getSnapshot, () => null)
}

export function setDemoUserId(userId: string) {
  try {
    window.localStorage.setItem(KEY, userId)
  } catch {
    // 저장 실패해도 데모 진행에는 영향 없음
  }
  listeners.forEach((l) => l())
}
