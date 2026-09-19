'use client'

import {
  createContext,
  useContext,
  useEffect,
  useSyncExternalStore,
  type ReactNode,
} from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { usePathname, useRouter } from 'next/navigation'
import { USE_MOCK } from '@/lib/api/http'
import { resolveCurrentUser } from '@/lib/api/auth'
import { AUTH_EXPIRED, clearAccessToken, getAccessToken, setAccessToken, subscribeAuth } from '@/lib/auth-token'

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
  currentUser: User | null
  users: User[]
  setCurrentUserId: (userId: string) => void
  isLoading: boolean
  signIn: (token: string) => void
  logout: () => void
}

const UserContext = createContext<UserContextValue | null>(null)

function MockUserProvider({
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
    isLoading: false,
    signIn: () => {},
    logout: () => {},
  }

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  )
}

function AuthenticatedUserProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const queryClient = useQueryClient()
  const token = useSyncExternalStore(subscribeAuth, getAccessToken, getServerSnapshot)
  const me = useQuery({
    queryKey: ['auth', 'me', token],
    queryFn: () => resolveCurrentUser(token),
    enabled: !!token,
    retry: false,
  })
  const usersQuery = useQuery({
    queryKey: ['users', me.data?.userId], queryFn: listUsers,
    enabled: !!token && !!me.data, retry: false,
  })
  const publicRoute = pathname === '/' || pathname === '/login' || pathname === '/signup'

  useEffect(() => {
    const expired = () => { queryClient.clear(); router.replace('/login') }
    const storageChanged = () => { queryClient.clear() }
    window.addEventListener(AUTH_EXPIRED, expired)
    window.addEventListener('storage', storageChanged)
    return () => {
      window.removeEventListener(AUTH_EXPIRED, expired)
      window.removeEventListener('storage', storageChanged)
    }
  }, [queryClient, router])

  useEffect(() => {
    if (!publicRoute && !getAccessToken()) router.replace('/login')
  }, [publicRoute, token, router])

  const currentUser = token ? me.data ?? null : null
  const value: UserContextValue = {
    currentUser, users: usersQuery.data ?? (currentUser ? [currentUser] : []),
    isLoading: !!token && me.isPending,
    setCurrentUserId: () => {}, // Demo selection cannot impersonate a real user.
    signIn: (accessToken) => { queryClient.clear(); setAccessToken(accessToken) },
    logout: () => { queryClient.clear(); clearAccessToken(); router.replace('/login') },
  }
  let content = children
  if (!publicRoute) {
    if (me.isError || usersQuery.isError) {
      content = <div className="p-6 text-center">사용자 정보를 불러오지 못했습니다.
        <button className="ml-2 underline" onClick={() => { void me.refetch(); void usersQuery.refetch() }}>다시 시도</button>
      </div>
    } else if (!currentUser || usersQuery.isPending) {
      content = <div className="p-6 text-center">로그인 정보를 확인하는 중…</div>
    }
  }
  return <UserContext.Provider value={value}>{content}</UserContext.Provider>
}

export function UserProvider({ children }: { children: ReactNode }) {
  return USE_MOCK ? <MockUserProvider>{children}</MockUserProvider> : <AuthenticatedUserProvider>{children}</AuthenticatedUserProvider>
}

export function useAuth(): UserContextValue {
  const context = useContext(UserContext)

  if (!context) {
    throw new Error(
      'useUser must be used within a UserProvider',
    )
  }

  return context
}

// Existing service components stay non-null; the provider gates protected routes.
export function useUser(): UserContextValue & { currentUser: User } {
  const context = useAuth()
  if (!context.currentUser) throw new Error('로그인이 필요합니다.')
  return { ...context, currentUser: context.currentUser }
}
