import type { Itinerary } from '@/lib/types'
import { categoryLabel } from '@/lib/categories'

export default function ItineraryResult({
  itinerary,
  memberNameById,
}: {
  itinerary: Itinerary
  memberNameById: Map<string, string>
}) {
  return (
    <div className="space-y-5">
      {itinerary.rebalanced && (
        <p className="rounded-lg bg-blue-50 px-3 py-2 text-xs font-medium text-blue-800">
          균형 보정됨 — 특정 멤버에게 치우친 일정을 다시 조율했어요.
        </p>
      )}
      {!itinerary.allMembersCovered && (
        <p role="alert" className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
          아직 일정에 취향이 반영되지 않은 멤버가 있어요.
        </p>
      )}

      {itinerary.days.map((day) => (
        <section key={day.day} className="space-y-3">
          {itinerary.days.length > 1 && (
            <h2 className="text-sm font-semibold text-slate-700">
              Day {day.day} · {day.date}
            </h2>
          )}
          <ol className="space-y-3">
            {day.items.map((item) => (
              <li key={item.order} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500">
                      {item.startTime} – {item.endTime}
                    </p>
                    <p className="mt-0.5 truncate text-base font-semibold text-slate-900">{item.place.name}</p>
                    {item.place.address && (
                      <p className="truncate text-xs text-slate-500">{item.place.address}</p>
                    )}
                  </div>
                  <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {categoryLabel(item.category)}
                  </span>
                </div>

                <p className="mt-2 text-sm text-slate-700">{item.reason}</p>

                {item.relatedUsers.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {item.relatedUsers.map((u) => (
                      <span
                        key={`${item.order}-${u.userId}`}
                        className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
                      >
                        {memberNameById.get(u.userId) ?? u.userId} · {u.preferenceLabel}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  )
}
