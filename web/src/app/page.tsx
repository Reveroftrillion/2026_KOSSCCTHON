import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function LandingPage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-8 px-4 py-10">
      <section>
        <h1 className="text-4xl font-bold text-slate-900">TripClip</h1>
        <p className="mt-2 text-lg text-slate-700">SNS 속 여행을 실제 여행으로</p>
        <p className="mt-3 text-sm leading-relaxed text-slate-500">
          친구들이 숏폼에서 저장한 장소를 한곳에 모으면, AI가 모두의 취향을 분석해
          한 사람에게 치우치지 않은 여행 일정을 만들어줘요.
        </p>
      </section>

      <Link href="/trips/new" className={cn(buttonVariants({ size: 'lg' }), 'w-full')}>
        여행방 만들기
      </Link>
    </main>
  )
}
