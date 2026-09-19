'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { buttonVariants } from '@/components/ui/button'
import { getTrip } from '@/lib/api/trips'
import { postGroupItinerary } from '@/lib/api/itinerary'
import type { Itinerary, ItineraryRequest } from '@/lib/types'
import { getTripContents } from './temp-contents'
import ItineraryGeneratingSteps from './ItineraryGeneratingSteps'
import ItineraryRequestForm from './ItineraryRequestForm'
import ItineraryResult from './ItineraryResult'
import { PageError, PageLoading } from './state-views'

export default function ItineraryPlanner({ tripId }: { tripId: string }) {
  // TripShell이 같은 키로 이미 불러왔으므로 보통 캐시에서 바로 나온다.
  const { data: trip } = useQuery({ queryKey: ['trip', tripId], queryFn: () => getTrip(tripId) })
  const {
    data: contents,
    isPending: contentsPending,
    isError: contentsError,
    refetch: refetchContents,
  } = useQuery({ queryKey: ['contents', tripId], queryFn: () => getTripContents(tripId) })

  const mutation = useMutation<Itinerary, Error, ItineraryRequest>({
    mutationFn: (request) => postGroupItinerary(tripId, request),
  })

  if (!trip) return null
  if (contentsPending) return <PageLoading label="장바구니를 불러오는 중…" />
  if (contentsError) {
    return <PageError message="장바구니를 불러오지 못했어요." onRetry={() => refetchContents()} />
  }

  if (mutation.isPending) {
    return <ItineraryGeneratingSteps />
  }

  if (mutation.isSuccess) {
    const memberNameById = new Map(trip.members.map((m) => [m.userId, m.name]))
    return (
      <div className="space-y-4">
        <ItineraryResult itinerary={mutation.data} memberNameById={memberNameById} />
        <button
          type="button"
          onClick={() => mutation.reset()}
          className={buttonVariants({ variant: 'outline', className: 'w-full' })}
        >
          다시 생성
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {mutation.isError && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {mutation.error instanceof Error ? mutation.error.message : '일정을 만들지 못했어요.'} 다시 시도해 주세요.
        </div>
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
