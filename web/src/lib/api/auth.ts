import type { User } from '@/lib/types'
import { http } from './http'

interface AuthUser { user_id: string; name: string; email: string }
interface LoginResponse { access_token: string; token_type: string; user: AuthUser }
const toUser = (user: AuthUser): User => ({ userId: user.user_id, name: user.name })

export async function signup(input: { name: string; email: string; password: string }): Promise<User> {
  const result = await http<AuthUser>('/api/users', { method: 'POST', auth: false, body: JSON.stringify(input) })
  return toUser(result)
}

export async function login(input: { email: string; password: string }): Promise<{ accessToken: string; user: User }> {
  const result = await http<LoginResponse>('/api/auth/login', { method: 'POST', auth: false, body: JSON.stringify(input) })
  return { accessToken: result.access_token, user: toUser(result.user) }
}

export async function getMe(token: string): Promise<User> {
  const result = await http<AuthUser>('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
  return toUser(result)
}

export async function resolveCurrentUser(token: string): Promise<User | null> {
  // Do not query /users or consult a demo user selection when no token exists.
  return token ? getMe(token) : null
}
