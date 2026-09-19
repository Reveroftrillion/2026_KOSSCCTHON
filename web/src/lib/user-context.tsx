'use client'

import {
  createContext,
  useContext,
  useSyncExternalStore,
  type ReactNode,
} from 'react'

import { useQuery } from '@tanstack/react-query'

import type { User } from '@/lib/types'
import { listUsers } from '@/lib/api/users'

const STORAGE_KEY = 'tripclip:current-user-id'

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback)

  return () => {
    window.removeEventListener('storage', callback)
  }
}

function getSnapshot(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

function getServerSnapshot(): string {
  return ''
}

interface UserContextValue {
  currentUser: User
  users: User[]
  setCurrentUserId: (userId: string) => void
}

const UserContext = createContext<UserContextValue | null>(null)

export function UserProvider({
  children,
}: {
  children: ReactNode
}) {
  const storedUserId = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  )

  const usersQuery = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  })

  if (usersQuery.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        사용자 정보를 불러오는 중…
      </div>
    )
  }

  if (usersQuery.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        사용자 정보를 불러오지 못했습니다.
      </div>
    )
  }

  const users = usersQuery.data

  if (users.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        등록된 사용자가 없습니다.
      </div>
    )
  }

  const currentUser =
    users.find(
      (user) => user.userId === storedUserId,
    ) ?? users[0]

  const setCurrentUserId = (userId: string) => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        userId,
      )
    } catch {
      // localStorage 실패 시 무시
    }

    window.dispatchEvent(
      new StorageEvent('storage', {
        key: STORAGE_KEY,
        newValue: userId,
      }),
    )
  }

  const value: UserContextValue = {
    currentUser,
    users,
    setCurrentUserId,
  }

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser(): UserContextValue {
  const context = useContext(UserContext)

  if (!context) {
    throw new Error(
      'useUser must be used within a UserProvider',
    )
  }

  return context
}