import { AUTH_EXPIRED, clearAccessToken, getAccessToken } from '../auth-token'

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'

// status 0 = 네트워크/타임아웃 등 응답 자체를 못 받은 경우
export class HttpError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'HttpError'
    this.status = status
  }
}

// AI 호출(일정 생성)은 수 초~수십 초 걸릴 수 있다.
const DEFAULT_TIMEOUT_MS = 60_000

type HttpInit = RequestInit & { timeoutMs?: number; auth?: boolean }

export async function http<T>(path: string, init?: HttpInit): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, auth = true, ...rest } = init ?? {}
  const headers = new Headers(rest.headers)
  headers.set('Content-Type', 'application/json')
  const token = !USE_MOCK && auth ? getAccessToken() : ''
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new HttpError(0, '서버 응답이 너무 늦어요. 잠시 후 다시 시도해 주세요.')
    }
    throw new HttpError(0, '서버에 연결할 수 없어요. 백엔드가 실행 중인지 확인해 주세요.')
  } finally {
    clearTimeout(timer)
  }

  if (!res.ok) {
    if (res.status === 401 && auth && !USE_MOCK && typeof window !== 'undefined') {
      // A late response from a previous login must not clear a newer session.
      const sent = headers.get('Authorization')
      if (!getAccessToken() || sent === `Bearer ${getAccessToken()}`) {
        clearAccessToken()
        window.dispatchEvent(new Event(AUTH_EXPIRED))
      }
    }
    // FastAPI는 {detail}, 그 외 {message}를 흔히 쓴다. 없으면 status만 보여준다.
    let detail = ''
    try {
      const body = (await res.json()) as { detail?: unknown; message?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map(item => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean).join(' / ')
      else if (typeof body.message === 'string') detail = body.message
    } catch {
      // 본문이 JSON이 아니면 무시
    }
    throw new HttpError(res.status, detail || `요청에 실패했어요. (${res.status})`)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
