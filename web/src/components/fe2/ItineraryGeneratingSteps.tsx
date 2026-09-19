'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

// SPEC 5-3: Content Parser → Preference Updater → Group Preference Builder →
// Itinerary Planner → Balance Checker. 화면에서는 뒤 3단계만 문구로 보여준다.
const STEPS = ['그룹 취향 분석 중', '일정 생성 중', '균형 점검 중']
const STEP_INTERVAL_MS = 1100

export default function ItineraryGeneratingSteps() {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))
    }, STEP_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [])

  return (
    <div role="status" aria-live="polite" className="rounded-xl border border-slate-200 p-6 shadow-sm">
      <ul className="space-y-3">
        {STEPS.map((label, i) => {
          const state = i < stepIndex ? 'done' : i === stepIndex ? 'active' : 'pending'
          return (
            <li key={label} className="flex items-center gap-3">
              <span
                className={cn(
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                  state === 'done' && 'bg-blue-600 text-white',
                  state === 'active' && 'animate-pulse bg-blue-100 text-blue-700',
                  state === 'pending' && 'bg-slate-100 text-muted-foreground/80',
                )}
              >
                {state === 'done' ? '✓' : i + 1}
              </span>
              <span
                className={cn(
                  'text-sm',
                  state === 'pending' ? 'text-muted-foreground/80' : 'text-foreground/95 font-medium',
                )}
              >
                {label}…
              </span>
            </li>
          )
        })}
      </ul>
      <span className="sr-only">AI가 그룹 취향을 분석하고 공동 일정을 만들고 있어요.</span>
    </div>
  )
}
