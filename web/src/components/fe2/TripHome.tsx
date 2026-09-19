'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { buttonVariants } from '@/components/ui/button'
import { getTrip } from '@/lib/api/trips'
import { cn } from '@/lib/utils'
import MemberAvatar from './MemberAvatar'
import { PageEmpty, PageError, PageLoading } from './state-views'
import { listTripContents } from '@/lib/api/contents'

export default function TripHome({ tripId }: { tripId: string }) {
  // TripShell이 같은 키로 이미 불러왔으므로 보통 캐시에서 바로 나온다.
  const { data: trip } = useQuery({ queryKey: ['trip', tripId], queryFn: () => getTrip(tripId) })
  const {
    data: contents,
    isPending,
    isError,
    refetch,
  } = useQuery({ queryKey: ['contents', tripId], queryFn: () => listTripContents(tripId) })

  if (!trip) return null
  if (isPending) return <PageLoading label="저장 현황을 불러오는 중…" />
  if (isError) return <PageError message="저장 현황을 불러오지 못했어요." onRetry={() => refetch()} />

  const counts = new Map<string, number>()
  for (const c of contents) counts.set(c.userId, (counts.get(c.userId) ?? 0) + 1)
  const waiting = trip.members.filter((m) => (counts.get(m.userId) ?? 0) === 0)

  if (contents.length === 0) {
    return (
      <PageEmpty title="아직 저장한 숏폼이 없어요" description="첫 숏폼을 담아보세요.">
        <Link href={`/trips/${tripId}/add`} className={buttonVariants()}>
          숏폼 담기
        </Link>
      </PageEmpty>
    )
  }

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">멤버별 저장 현황</h2>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {trip.members.map((m) => (
            <li key={m.userId} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <MemberAvatar name={m.name} />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{m.name}</p>
                <p className="text-xs text-slate-500">{counts.get(m.userId) ?? 0}건 저장</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section
        className={cn(
          'rounded-xl p-4 text-sm',
          waiting.length === 0 ? 'bg-blue-50 text-blue-900' : 'bg-amber-50 text-amber-900',
        )}
      >
        {waiting.length === 0 ? (
          <>
            <p className="font-semibold">그룹 취향을 분석할 수 있어요</p>
            <p className="mt-1">모든 멤버가 숏폼을 저장했어요. 공통 취향과 개인 취향을 확인해 보세요.</p>
          </>
        ) : (
          <>
            <p className="font-semibold">아직 저장하지 않은 멤버가 있어요</p>
            <p className="mt-1">
              {waiting.map((m) => m.name).join(', ')}님이 숏폼을 저장하면 그룹 분석이 더 정확해져요.
            </p>
          </>
        )}
      </section>

      <div className="grid grid-cols-2 gap-2">
        <Link href={`/trips/${tripId}/add`} className={cn(buttonVariants({ variant: 'outline' }), 'w-full')}>
          숏폼 담기
        </Link>
        <Link href={`/trips/${tripId}/group`} className={cn(buttonVariants(), 'w-full')}>
          그룹 취향 보기
        </Link>
      </div>
    </div>
  )
}
