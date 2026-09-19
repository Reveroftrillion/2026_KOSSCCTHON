import type { GroupPreferences } from '@/lib/types'
import { categoryLabel } from '@/lib/categories'
import { cn } from '@/lib/utils'
import MemberAvatar from './MemberAvatar'

// 셀 배경색의 최소 진하기. 값이 0에 가까워도 칸의 존재는 보이게 한다.
const MIN_INTENSITY = 0.12

export default function GroupPreferenceMatrix({ data }: { data: GroupPreferences }) {
  const { matrix, common, unique, members } = data
  const nameByUserId = new Map(members.map((m) => [m.userId, m.name]))
  const labelByKey = new Map(members.flatMap((m) => m.top).map((p) => [p.key, p.label]))
  const commonKeys = new Set(common.map((c) => c.key))
  const uniqueByUserKey = new Map(unique.map((u) => [`${u.userId}:${u.key}`, u]))

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-700">취향 매트릭스</h2>
        <p className="mt-1 text-xs text-slate-500">
          값은 각자의 취향 중 가장 높은 항목을 100으로 둔 상대 점수예요.
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[420px] border-collapse text-sm">
          <thead>
            <tr>
              <th
                scope="col"
                className="w-20 border-b border-slate-200 p-2 text-left text-xs font-medium text-slate-500"
              >
                카테고리
              </th>
              {matrix.userIds.map((userId) => (
                <th key={userId} scope="col" className="border-b border-slate-200 p-2 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <MemberAvatar name={nameByUserId.get(userId) ?? userId} size="sm" />
                    <span className="text-xs font-medium text-slate-700">
                      {nameByUserId.get(userId) ?? userId}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.keys.map((key, rowIndex) => (
              <tr key={key}>
                <th
                  scope="row"
                  className="border-b border-slate-100 p-2 text-left align-top text-sm font-medium text-slate-800"
                >
                  <div className="flex flex-wrap items-center gap-1">
                    {labelByKey.get(key) ?? categoryLabel(key)}
                    {commonKeys.has(key) && (
                      <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                        공통
                      </span>
                    )}
                  </div>
                </th>
                {matrix.userIds.map((userId, colIndex) => {
                  const value = matrix.values[colIndex]?.[rowIndex] ?? 0
                  const isUnique = uniqueByUserKey.has(`${userId}:${key}`)
                  return (
                    <td key={userId} className="border-b border-slate-100 p-2 text-center align-top">
                      <div
                        className={cn(
                          'mx-auto flex h-9 w-14 items-center justify-center rounded-lg text-sm font-semibold',
                          value === 0 ? 'text-slate-400' : 'text-white',
                        )}
                        style={
                          value > 0
                            ? { backgroundColor: `rgba(13, 148, 136, ${Math.max(value / 100, MIN_INTENSITY)})` }
                            : undefined
                        }
                      >
                        {value}
                      </div>
                      {isUnique && <p className="mt-1 text-[10px] font-medium text-orange-600">개인 고유</p>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">
        진한 칸일수록 그 사람의 취향에서 비중이 크다는 뜻이에요. 민트 배지는 2명 이상의 공통 취향, 산호색
        글자는 특정 멤버만 뚜렷하게 강한 개인 고유 취향이에요.
      </p>
    </div>
  )
}
