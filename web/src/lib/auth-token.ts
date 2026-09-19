// Browser-only access-token storage. The old demo user ID is never authentication.
export const TOKEN_KEY = 'tripclip:access-token'
export const AUTH_CHANGED = 'tripclip:auth-changed'
export const AUTH_EXPIRED = 'tripclip:auth-expired'

export function getAccessToken(): string {
  if (typeof window === 'undefined') return ''
  try { return window.localStorage.getItem(TOKEN_KEY) ?? '' } catch { return '' }
}

export function setAccessToken(token: string): void {
  // Fail visibly if storage is unavailable instead of claiming login succeeded.
  window.localStorage.setItem(TOKEN_KEY, token)
  window.dispatchEvent(new Event(AUTH_CHANGED))
}

export function clearAccessToken(): void {
  if (typeof window === 'undefined') return
  try { window.localStorage.removeItem(TOKEN_KEY) } catch { /* Storage may be disabled. */ }
  window.dispatchEvent(new Event(AUTH_CHANGED))
}

export function subscribeAuth(callback: () => void): () => void {
  window.addEventListener(AUTH_CHANGED, callback)
  window.addEventListener('storage', callback)
  return () => {
    window.removeEventListener(AUTH_CHANGED, callback)
    window.removeEventListener('storage', callback)
  }
}
