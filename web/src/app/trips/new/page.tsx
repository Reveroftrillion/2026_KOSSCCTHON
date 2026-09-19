import Link from 'next/link'
import NewTripForm from '@/components/fe2/NewTripForm'

export default function NewTripPage() {
  return (
    <main className="mx-auto w-full max-w-md px-4 py-8">
      <Link href="/" className="text-sm text-slate-500 hover:text-slate-700">
        ← 처음으로
      </Link>
      <h1 className="mt-3 text-2xl font-extrabold tracking-tight text-slate-900">여행방 만들기</h1>
      <p className="mt-1 mb-6 text-sm text-slate-500">
        목적지와 기간, 함께 갈 친구들을 정해요.
      </p>
      <NewTripForm />
    </main>
  )
}
