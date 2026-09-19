export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true'

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    throw new Error(`요청에 실패했어요. (${res.status})`)
  }
  return (await res.json()) as T
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
