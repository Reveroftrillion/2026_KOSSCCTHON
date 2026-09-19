'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import type { Content, ItineraryRequest } from '@/lib/types'
import { categoryLabel } from '@/lib/categories'

const schema = z
  .object({
    date: z.string().optional(),
    area: z.string().trim().min(1, '지역을 입력해 주세요.'),
    startTime: z.string().min(1, '시작 시간을 선택해 주세요.'),
    endTime: z.string().min(1, '종료 시간을 선택해 주세요.'),
    budget: z.string().optional(),
    includeMeals: z.boolean(),
    mustVisitContentIds: z.array(z.string()),
  })
  .refine((v) => !v.startTime || !v.endTime || v.endTime > v.startTime, {
    path: ['endTime'],
    message: '종료 시간은 시작 시간보다 이후여야 해요.',
  })

type FormValues = z.infer<typeof schema>

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return (
    <p role="alert" className="mt-1 text-xs text-red-600">
      {message}
    </p>
  )
}

export default function ItineraryRequestForm({
  defaultArea,
  defaultDate, endDate, defaultStartTime, defaultEndTime, realMode = false,
  contents,
  isSubmitting,
  onSubmit,
}: {
  defaultArea?: string
  defaultDate?: string; endDate?: string; defaultStartTime?: string; defaultEndTime?: string; realMode?: boolean
  contents: Content[]
  isSubmitting: boolean
  onSubmit: (request: ItineraryRequest) => void
}) {
  const {
    register,
    watch,
    setValue,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      area: defaultArea ?? '',
      date: defaultDate,
      startTime: defaultStartTime ?? '13:00',
      endTime: defaultEndTime ?? '20:00',
      budget: '',
      includeMeals: !realMode,
      mustVisitContentIds: [],
    },
  })

  const includeMeals = watch('includeMeals')
  const mustVisitContentIds = watch('mustVisitContentIds')

  function toggleMustVisit(contentId: string) {
    setValue(
      'mustVisitContentIds',
      mustVisitContentIds.includes(contentId)
        ? mustVisitContentIds.filter((id) => id !== contentId)
        : [...mustVisitContentIds, contentId],
      { shouldDirty: true },
    )
  }

  function submit(values: FormValues) {
    const budget = values.budget?.trim() ? Number(values.budget) : undefined
    onSubmit({
      date: values.date,
      area: values.area.trim(),
      startTime: values.startTime,
      endTime: values.endTime,
      budget: budget && Number.isFinite(budget) ? budget : undefined,
      includeMeals: values.includeMeals,
      mustVisitContentIds: values.mustVisitContentIds,
    })
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-5" noValidate>
      {realMode && (
        <div>
          <Label htmlFor="itineraryDate">일정 날짜</Label>
          <Input id="itineraryDate" type="date" min={defaultDate} max={endDate} {...register('date')} />
          <p className="mt-2 text-xs text-slate-500">지역과 시간은 여행방 설정을 사용해요. 예산·식사·필수 장소 지정은 아직 지원하지 않아요.</p>
        </div>
      )}
      <div>
        <Label htmlFor="area">지역</Label>
        <Input id="area" placeholder="예: 성수" readOnly={realMode} className="mt-1" {...register('area')} />
        <FieldError message={errors.area?.message} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="min-w-0">
          <Label htmlFor="startTime">시작 시간</Label>
          <Input id="startTime" type="time" readOnly={realMode} className="mt-1" {...register('startTime')} />
          <FieldError message={errors.startTime?.message} />
        </div>
        <div className="min-w-0">
          <Label htmlFor="endTime">종료 시간</Label>
          <Input id="endTime" type="time" readOnly={realMode} className="mt-1" {...register('endTime')} />
          <FieldError message={errors.endTime?.message} />
        </div>
      </div>

      {!realMode && <div className="space-y-5">
      <div>
        <Label htmlFor="budget">1인 예산 (선택, 원)</Label>
        <Input id="budget" type="number" min={0} placeholder="예: 50000" className="mt-1" {...register('budget')} />
      </div>

      <div>
        <p className="text-sm font-medium">저녁 식사 포함</p>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            aria-pressed={includeMeals}
            onClick={() => setValue('includeMeals', true)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-sm transition-colors',
              includeMeals
                ? 'border-blue-600 bg-blue-600 text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
            )}
          >
            포함
          </button>
          <button
            type="button"
            aria-pressed={!includeMeals}
            onClick={() => setValue('includeMeals', false)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-sm transition-colors',
              !includeMeals
                ? 'border-blue-600 bg-blue-600 text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
            )}
          >
            미포함
          </button>
        </div>
      </div>

      <div>
        <p className="text-sm font-medium">필수 장소 (장바구니에서 선택, 선택 사항)</p>
        {contents.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">아직 저장된 숏폼이 없어요.</p>
        ) : (
          <div className="mt-2 space-y-2">
            {contents.map((content) => {
              const checked = mustVisitContentIds.includes(content.contentId)
              return (
                <button
                  key={content.contentId}
                  type="button"
                  aria-pressed={checked}
                  onClick={() => toggleMustVisit(content.contentId)}
                  className={cn(
                    'flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                    checked
                      ? 'border-blue-600 bg-blue-50 text-blue-800'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
                  )}
                >
                  <span className="truncate">{content.place.name}</span>
                  <span className="ml-2 shrink-0 text-xs text-slate-400">
                    {categoryLabel(content.category)}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      </div>}
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? '일정 만드는 중…' : '공동 일정 만들기'}
      </Button>
    </form>
  )
}
