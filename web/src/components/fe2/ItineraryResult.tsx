'use client'

import { useEffect, useRef, useState } from 'react'
import type { Itinerary } from '@/lib/types'
import { categoryLabel } from '@/lib/categories'
import { cn } from '@/lib/utils'
import ItineraryMap from './ItineraryMap'
import ReflectionPanel from './ReflectionPanel'

export default function ItineraryResult({
  itinerary,
  memberNameById,
}: {
  itinerary: Itinerary
  memberNameById: Map<string, string>
}) {
  return (
    <div className="space-y-5">
      <ReflectionPanel itinerary={itinerary} />

      {itinerary.days.map((day) => (
        <DayTimeline
          key={day.day}
          day={day}
          showDayHeader={itinerary.days.length > 1}
          memberNameById={memberNameById}
        />
      ))}
    </div>
  )
}

function DayTimeline({
  day,
  showDayHeader,
  memberNameById,
}: {
  day: Itinerary['days'][number]
  showDayHeader: boolean
  memberNameById: Map<string, string>
}) {
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null)
  const itemRefs = useRef(new Map<number, HTMLLIElement>())

  // 지도 마커를 클릭했을 때 해당 카드로 스크롤해 포커스를 맞춘다.
  useEffect(() => {
    if (selectedOrder == null) return
    itemRefs.current.get(selectedOrder)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedOrder])

  if (day.items.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
        이 날짜에는 생성된 일정 항목이 없어요.
      </p>
    )
  }

  return (
    <section className="space-y-3">
      {showDayHeader && (
        <h2 className="text-sm font-semibold text-slate-700">
          Day {day.day} · {day.date}
        </h2>
      )}

      <ItineraryMap items={day.items} selectedOrder={selectedOrder} onSelect={setSelectedOrder} />

      <ol className="space-y-3">
        {day.items.map((item) => {
          const active = item.order === selectedOrder
          return (
            <li
              key={item.order}
              ref={(el) => {
                if (el) itemRefs.current.set(item.order, el)
                else itemRefs.current.delete(item.order)
              }}
              onClick={() => setSelectedOrder(item.order)}
              className={cn(
                'cursor-pointer rounded-xl border bg-white p-4 transition-colors',
                active ? 'border-blue-500 ring-2 ring-blue-100' : 'border-slate-200',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-500">
                    {item.startTime} – {item.endTime}
                  </p>
                  <p className="mt-0.5 truncate text-base font-semibold text-slate-900">
                    <span
                      className={cn(
                        'mr-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white',
                        active ? 'bg-blue-700' : 'bg-blue-500',
                      )}
                    >
                      {item.order}
                    </span>
                    {item.place.name}
                  </p>
                  {item.place.address && <p className="truncate text-xs text-slate-500">{item.place.address}</p>}
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
                      key={`${item.order}-${u.userId}-${u.preferenceKey}`}
                      className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
                    >
                      {memberNameById.get(u.userId) ?? u.userId} · {u.preferenceLabel}
                    </span>
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}
