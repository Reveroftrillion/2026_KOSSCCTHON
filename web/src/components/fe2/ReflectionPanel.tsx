import type { Itinerary } from '@/lib/types'
import { cn } from '@/lib/utils'
import MemberAvatar from './MemberAvatar'

// SPEC 3장 규칙 3: 반영도는 서버 값(reflectionPercent, coveredTop/totalTop)만 표시한다.
// 여기서는 계산하지 않고, 막대 폭을 위해 0~100 범위로 자르기만 한다.
function clampPercent(v: number): number {
  if (!Number.isFinite(v)) return 0
  return Math.min(100, Math.max(0, Math.round(v)))
}

export default function ReflectionPanel({ itinerary }: { itinerary: Itinerary }) {
  const { reflection, allMembersCovered, rebalanced } = itinerary

  return (
    <section aria-labelledby="reflection-heading" className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="reflection-heading" className="text-sm font-semibold text-slate-800">
          사람별 취향 반영도
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {rebalanced && (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">균형 보정됨</span>
          )}
          <span
            className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              allMembersCovered ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800',
            )}
          >
            {allMembersCovered ? '모든 멤버 반영' : '미반영 멤버 있음'}
          </span>
        </div>
      </div>

      {rebalanced && (
        <p className="mt-2 text-xs text-slate-500">특정 멤버에게 치우친 일정을 AI가 다시 조율했어요.</p>
      )}

      {!allMembersCovered && (
        <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
          일정에 취향이 한 번도 반영되지 않은 멤버가 있어요. 조건을 바꿔 다시 생성해 보세요.
        </p>
      )}

      {reflection.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">반영도 정보가 없어요.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {reflection.map((r) => {
            const percent = clampPercent(r.reflectionPercent)
            const uncovered = r.coveredTop === 0
            return (
              <li key={r.userId} className="flex items-center gap-3">
                <MemberAvatar name={r.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="truncate text-sm font-medium text-slate-800">{r.name}</p>
                    <p
                      className={cn(
                        'shrink-0 text-sm font-semibold tabular-nums',
                        uncovered ? 'text-amber-700' : 'text-blue-700',
                      )}
                    >
                      {percent}%
                    </p>
                  </div>
                  <div
                    role="progressbar"
                    aria-label={`${r.name} 취향 반영도`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percent}
                    className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100"
                  >
                    <div
                      className={cn('h-full rounded-full transition-[width]', uncovered ? 'bg-amber-400' : 'bg-blue-500')}
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    상위 취향 {r.totalTop}개 중 {r.coveredTop}개 반영
                    {uncovered && ' · 아직 반영된 취향이 없어요'}
                  </p>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
