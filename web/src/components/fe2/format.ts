// 'YYYY-MM-DD'를 타임존 영향 없이 다룬다.
function parse(date: string): { y: number; m: number; d: number } {
  const [y, m, d] = date.split('-').map(Number)
  return { y, m, d }
}

export function formatDateRange(startDate: string, endDate: string): string {
  const s = parse(startDate)
  const e = parse(endDate)
  const start = `${s.m}월 ${s.d}일`
  const end = s.m === e.m && s.y === e.y ? `${e.d}일` : `${e.m}월 ${e.d}일`
  const nights = Math.round((Date.UTC(e.y, e.m - 1, e.d) - Date.UTC(s.y, s.m - 1, s.d)) / 86_400_000)
  const span = nights <= 0 ? '당일' : `${nights}박 ${nights + 1}일`
  return `${start}${nights <= 0 ? '' : ` ~ ${end}`} (${span})`
}
