'use client'

import { DEMO_USERS } from '@/lib/mocks/trips'
import { cn } from '@/lib/utils'
import { setDemoUserId, useDemoUserId } from './use-demo-user'

export default function DemoUserPicker() {
  const selected = useDemoUserId()

  return (
    <div>
      <p className="mb-2 text-sm font-medium text-slate-700">데모 사용자 선택</p>
      <div className="grid grid-cols-3 gap-2">
        {DEMO_USERS.map((user) => {
          const active = user.userId === selected
          return (
            <button
              key={user.userId}
              type="button"
              aria-pressed={active}
              onClick={() => setDemoUserId(user.userId)}
              className={cn(
                'flex flex-col items-center gap-1 rounded-xl border p-3 text-sm transition-colors',
                active
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
              )}
            >
              <span
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-full text-base font-semibold text-white',
                  active ? 'bg-blue-600' : 'bg-slate-400',
                )}
              >
                {user.name.slice(0, 1)}
              </span>
              {user.name}
            </button>
          )
        })}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        로그인 없이 데모용 사용자 중 한 명으로 체험해요.
      </p>
    </div>
  )
}
