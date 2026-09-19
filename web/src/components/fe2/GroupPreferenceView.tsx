'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { buttonVariants } from '@/components/ui/button'
import { getGroupPreferences } from '@/lib/api/preferences'
import { categoryLabel } from '@/lib/categories'
import GroupPreferenceMatrix from './GroupPreferenceMatrix'
import { PageEmpty, PageError, PageLoading } from './state-views'

// 함수명 그대로 조사입니다. 암튼 그렇습니다.
function josa(word: string, a: string, b: string): string {
  const code = word.charCodeAt(word.length - 1) - 0xac00
  return code >= 0 && code <= 11171 && code % 28 !== 0 ? a : b
}

export default function GroupPreferenceView({ tripId }: { tripId: string }) {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['groupPreferences', tripId],
    queryFn: () => getGroupPreferences(tripId),
  })

  if (isPending) return <PageLoading label="그룹 취향을 분석하는 중…" />

  if (isError) {
    return (
      <PageError
        message={error instanceof Error ? error.message : '그룹 취향을 불러오지 못했어요.'}
        onRetry={() => refetch()}
      />
    )
  }

  if (!data || data.matrix.userIds.length === 0 || data.matrix.keys.length === 0) {
    return (
      <PageEmpty
        title="아직 비교할 취향 데이터가 없어요"
        description="멤버들이 숏폼을 저장하면 그룹 취향을 비교할 수 있어요."
      />
    )
  }

  const nameById = new Map(data.members.map((m) => [m.userId, m.name]))
  const labelByKey = new Map(data.members.flatMap((m) => m.top).map((p) => [p.key, p.label]))

  const commonSentences = data.common.map((c) => {
    const names = c.memberIds.map((id) => nameById.get(id) ?? id)
    return `${c.label}${josa(c.label, '은', '는')} ${names.join(', ')}의 공통 취향이에요.`
  })

  const uniqueSentences = data.unique.map((u) => {
    const name = nameById.get(u.userId) ?? u.userId
    return `${u.label}${josa(u.label, '은', '는')} ${name}만의 뚜렷한 개인 고유 취향이에요.`
  })

  // 공통도 개인 고유도 아닌 항목: 서버가 준 매트릭스에서 가장 높은 멤버만 찾아 사실대로 표현한다.
  // ("무난하게 수용 가능" 같은 데이터로 확인되지 않은 주장은 하지 않는다.)
  const otherSentences = data.matrix.keys.flatMap((key, keyIndex) => {
    const isCommon = data.common.some((c) => c.key === key)
    const isUnique = data.unique.some((u) => u.key === key)
    if (isCommon || isUnique) return []

    let leaderIndex = 0
    data.matrix.userIds.forEach((_, userIndex) => {
      const value = data.matrix.values[userIndex]?.[keyIndex] ?? 0
      const best = data.matrix.values[leaderIndex]?.[keyIndex] ?? 0
      if (value > best) leaderIndex = userIndex
    })
    const leaderId = data.matrix.userIds[leaderIndex]
    const leaderName = nameById.get(leaderId) ?? leaderId
    const label = labelByKey.get(key) ?? categoryLabel(key)

    return [
      `${label}${josa(label, '은', '는')} ${leaderName}의 취향이 가장 높아요. 다른 멤버의 취향과 함께 조율해 일정에 반영해요.`,
    ]
  })

  return (
    <div className="space-y-5">
      <GroupPreferenceMatrix data={data} />

      <section className="rounded-xl border border-slate-200 p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-foreground/90">해석</h2>
        {commonSentences.length === 0 && uniqueSentences.length === 0 && otherSentences.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            아직 뚜렷한 공통·개인 고유 취향을 찾지 못했어요. 숏폼을 더 저장하면 더 정확해져요.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5 text-sm text-foreground/90">
            {commonSentences.map((s) => (
              <li key={s} className="flex gap-1.5">
                <span className="mt-0.5 shrink-0 rounded-full bg-blue-100 px-1.5 text-[10px] font-semibold text-blue-700">
                  공통
                </span>
                {s}
              </li>
            ))}
            {uniqueSentences.map((s) => (
              <li key={s} className="flex gap-1.5">
                <span className="mt-0.5 shrink-0 rounded-full bg-orange-100 px-1.5 text-[10px] font-semibold text-orange-700">
                  개인
                </span>
                {s}
              </li>
            ))}
            {otherSentences.map((s) => (
              <li key={s} className="flex gap-1.5 text-muted-foreground">
                <span className="mt-0.5 shrink-0 rounded-full bg-slate-100 px-1.5 text-[10px] font-semibold text-foreground/80">
                  기타
                </span>
                {s}
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link href={`/trips/${tripId}/itinerary`} className={buttonVariants({ size: 'lg', className: 'w-full' })}>
        이 취향으로 일정 만들기
      </Link>
    </div>
  )
}