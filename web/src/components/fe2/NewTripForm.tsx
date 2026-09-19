'use client'

import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createTrip } from '@/lib/api/trips'
import { useUser } from '@/lib/user-context'
import { cn } from '@/lib/utils'

const schema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, '여행 이름을 입력해 주세요.')
      .max(40, '40자 이내로 입력해 주세요.'),

    destination: z
      .string()
      .trim()
      .min(1, '목적지를 입력해 주세요.'),

    startDate: z
      .string()
      .min(1, '시작일을 선택해 주세요.'),

    endDate: z
      .string()
      .min(1, '종료일을 선택해 주세요.'),

    memberIds: z
      .array(z.string())
      .min(2, '멤버를 2명 이상 선택해 주세요.')
      .max(4, '멤버는 최대 4명까지 선택할 수 있어요.'),
  })
  .refine(
    (v) =>
      !v.startDate ||
      !v.endDate ||
      v.endDate >= v.startDate,
    {
      path: ['endDate'],
      message:
        '종료일은 시작일과 같거나 이후여야 해요.',
    },
  )

type FormValues = z.infer<typeof schema>

function FieldError({
  message,
}: {
  message?: string
}) {
  if (!message) return null

  return (
    <p
      role="alert"
      className="mt-1 text-xs text-red-600"
    >
      {message}
    </p>
  )
}

export default function NewTripForm() {
  const router = useRouter()

  const {
    currentUser,
    users,
  } = useUser()

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),

    defaultValues: {
      name: '',
      destination: '',
      startDate: '',
      endDate: '',

      // 실제 Backend에서 받아온 사용자들을 기본 선택
      memberIds: users.map(
        (user) => user.userId,
      ),
    },
  })

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createTrip({
        ...values,

        // 현재 선택된 사용자가 방장
        ownerUserId:
          currentUser.userId,
      }),

    onSuccess: (trip) => {
      router.push(
        `/trips/${trip.tripId}`,
      )
    },
  })

  return (
    <form
      onSubmit={handleSubmit(
        (values) =>
          mutation.mutate(values),
      )}
      className="space-y-5"
      noValidate
    >
      <div>
        <Label htmlFor="name">
          여행 이름
        </Label>

        <Input
          id="name"
          placeholder="예: 성수 데이 트립"
          className="mt-1"
          {...register('name')}
        />

        <FieldError
          message={errors.name?.message}
        />
      </div>

      <div>
        <Label htmlFor="destination">
          목적지
        </Label>

        <Input
          id="destination"
          placeholder="예: 서울 성수동"
          className="mt-1"
          {...register('destination')}
        />

        <FieldError
          message={
            errors.destination?.message
          }
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="min-w-0">
          <Label htmlFor="startDate">
            시작일
          </Label>

          <Input
            id="startDate"
            type="date"
            className="mt-1"
            {...register('startDate')}
          />

          <FieldError
            message={
              errors.startDate?.message
            }
          />
        </div>

        <div className="min-w-0">
          <Label htmlFor="endDate">
            종료일
          </Label>

          <Input
            id="endDate"
            type="date"
            className="mt-1"
            {...register('endDate')}
          />

          <FieldError
            message={
              errors.endDate?.message
            }
          />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium">
          멤버 (2~4명)
        </p>

        <Controller
          control={control}
          name="memberIds"
          render={({ field }) => (
            <div className="mt-2 flex flex-wrap gap-2">
              {users.map((user) => {
                const checked =
                  field.value.includes(
                    user.userId,
                  )

                const isOwner =
                  user.userId ===
                  currentUser.userId

                return (
                  <button
                    key={user.userId}
                    type="button"
                    aria-pressed={checked}

                    onClick={() => {
                      // 방장은 여행 멤버에서 제외할 수 없게 처리
                      if (isOwner) {
                        return
                      }

                      field.onChange(
                        checked
                          ? field.value.filter(
                            (id) =>
                              id !==
                              user.userId,
                          )
                          : [
                            ...field.value,
                            user.userId,
                          ],
                      )
                    }}

                    className={cn(
                      'rounded-full border px-4 py-1.5 text-sm transition-colors',

                      checked
                        ? 'border-blue-600 bg-blue-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',

                      isOwner &&
                      'cursor-default',
                    )}
                  >
                    {user.name}

                    {isOwner && (
                      <span className="ml-1 text-xs opacity-80">
                        (방장)
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        />

        <FieldError
          message={
            errors.memberIds?.message
          }
        />
      </div>

      {mutation.isError && (
        <div
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {mutation.error instanceof Error
            ? mutation.error.message
            : '여행방을 만들지 못했어요.'}{' '}
          다시 시도해 주세요.
        </div>
      )}

      <Button
        type="submit"
        size="lg"
        className="w-full"
        disabled={mutation.isPending}
      >
        {mutation.isPending
          ? '여행방 만드는 중…'
          : mutation.isError
            ? '다시 시도'
            : '여행방 만들기'}
      </Button>
    </form>
  )
}