import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'

// 임시 상태 화면. FE1의 공통 LoadingSteps/EmptyState/ErrorState(C-05)가 나오면 교체한다.
export function PageLoading({ label = '불러오는 중…' }: { label?: string }) {
  return (
    <div role="status" className="space-y-3 py-6" aria-live="polite">
      <div className="h-6 w-1/2 animate-pulse rounded bg-slate-200" />
      <div className="h-4 w-1/3 animate-pulse rounded bg-slate-200" />
      <div className="h-24 animate-pulse rounded-xl bg-slate-200" />
      <span className="sr-only">{label}</span>
    </div>
  )
}

export function PageError({
  message = '문제가 생겼어요.',
  onRetry,
  children,
}: {
  message?: string
  onRetry?: () => void
  children?: ReactNode
}) {
  return (
    <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
      <p>{message}</p>
      <div className="mt-3 flex gap-2">
        {onRetry && (
          <Button type="button" onClick={onRetry}>
            다시 시도
          </Button>
        )}
        {children}
      </div>
    </div>
  )
}

export function PageEmpty({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: ReactNode
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
      <p className="font-semibold text-foreground/95">{title}</p>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      {children && <div className="mt-4 flex justify-center">{children}</div>}
    </div>
  )
}
