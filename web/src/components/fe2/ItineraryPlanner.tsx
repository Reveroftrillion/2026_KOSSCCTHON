'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { buttonVariants } from '@/components/ui/button'
import { getTrip } from '@/lib/api/trips'
import { getTripItinerary, postGroupItinerary } from '@/lib/api/itinerary'
import type { Itinerary, ItineraryRequest } from '@/lib/types'
import { listTripContents } from '@/lib/api/contents'
import { cn } from '@/lib/utils'
import ItineraryGeneratingSteps from './ItineraryGeneratingSteps'
import ItineraryRequestForm from './ItineraryRequestForm'
import ItineraryResult from './ItineraryResult'
import { PageError, PageLoading } from './state-views'

export default function ItineraryPlanner({ tripId }: { tripId: string }) {
  const queryClient = useQueryClient()
  // 결과가 있어도 "다시 생성"을 누르면 조건 폼을 다시 보여준다.
  const [editing, setEditing] = useState(false)

  // TripShell이 같은 키로 이미 불러왔으므로 보통 캐시에서 바로 나온다.
  const { data: trip } = useQuery({ queryKey: ['trip', tripId], queryFn: () => getTrip(tripId) })

  const contentsQuery = useQuery({
    queryKey: ['contents', tripId],
    queryFn: () => listTripContents(tripId),
  })

  // 재진입/새로고침 시 최신 일정 복원. 없으면 null.
  const latestQuery = useQuery<Itinerary | null>({
    queryKey: ['itinerary', tripId],
    queryFn: () => getTripItinerary(tripId),
    retry: 1,
  })

  const mutation = useMutation<Itinerary, Error, ItineraryRequest>({
    mutationFn: (request) => postGroupItinerary(tripId, request),
    onSuccess: (itinerary) => {
      queryClient.setQueryData<Itinerary | null>(['itinerary', tripId], itinerary)
      setEditing(false)
    },
  })

  if (!trip) return null

  if (contentsQuery.isPending || latestQuery.isPending) {
    return <PageLoading label="일정을 불러오는 중…" />
  }

  if (contentsQuery.isError) {
    return <PageError message="장바구니를 불러오지 못했어요." onRetry={() => contentsQuery.refetch()} />
  }

  if (latestQuery.isError) {
    return (
      <PageError
        message={
          latestQuery.error instanceof Error ? latestQuery.error.message : '이전 일정을 불러오지 못했어요.'
        }
        onRetry={() => latestQuery.refetch()}
      >
        <button
          type="button"
          onClick={() => queryClient.setQueryData<Itinerary | null>(['itinerary', tripId], null)}
          className={cn(buttonVariants({ variant: 'outline' }))}
        >
          새 일정 만들기
        </button>
      </PageError>
    )
  }

  if (mutation.isPending) {
    return <ItineraryGeneratingSteps />
  }

  const itinerary = latestQuery.data ?? null
  const contents = contentsQuery.data

  if (itinerary && !editing) {
    const memberNameById = new Map(trip.members.map((m) => [m.userId, m.name]))
    return (
      <div className="space-y-4">
        <ItineraryResult itinerary={itinerary} memberNameById={memberNameById} />
        <button
          type="button"
          onClick={() => setEditing(true)}
          className={cn(buttonVariants({ variant: 'outline' }), 'w-full')}
        >
          다시 생성
        </button>
      </div>
    )
  }

  // 빈 상태(아직 일정 없음) 또는 다시 생성 모드: 조건 입력 폼
  return (
    <div className="space-y-4">
      {itinerary ? (
        <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <span className="min-w-0">조건을 바꿔 다시 만들어요. 새 일정이 만들어지면 기존 일정은 대체돼요.</span>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="shrink-0 font-medium text-blue-700 hover:underline"
          >
            기존 일정 보기
          </button>
        </div>
      ) : (
        <p className="text-sm text-foreground/80">
          아직 만들어진 일정이 없어요. 조건을 입력하면 그룹 취향을 바탕으로 AI가 공동 일정을 만들어요.
        </p>
      )}

      {mutation.isError && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {mutation.error instanceof Error ? mutation.error.message : '일정을 만들지 못했어요.'} 다시 시도해 주세요.
        </div>
      )}

      {contents.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-xs text-muted-foreground">
          저장된 숏폼이 없어도 그룹 취향만으로 일정을 만들 수 있어요. 필수 장소를 고르려면 먼저 숏폼을 담아 주세요.
        </p>
      )}

      <ItineraryRequestForm
        defaultArea={trip.destination}
        contents={contents}
        isSubmitting={mutation.isPending}
        onSubmit={(request) => mutation.mutate(request)}
      />
    </div>
  )
}
