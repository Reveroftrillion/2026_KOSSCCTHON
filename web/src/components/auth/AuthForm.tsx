'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { login, signup } from '@/lib/api/auth'
import { USE_MOCK } from '@/lib/api/http'
import { useAuth } from '@/lib/user-context'

export default function AuthForm({ mode, registered = false }: { mode: 'login' | 'signup'; registered?: boolean }) {
  const signingUp = mode === 'signup'
  const router = useRouter()
  const { signIn } = useAuth()
  const [error, setError] = useState('')
  const schema = z.object({
    name: z.string().trim().max(100).optional(),
    email: z.string().trim().email('올바른 이메일을 입력해 주세요.').max(100),
    password: z.string().min(signingUp ? 6 : 1, signingUp ? '비밀번호는 6자 이상이어야 해요.' : '비밀번호를 입력해 주세요.')
      .refine(value => new TextEncoder().encode(value).length <= 72, '비밀번호는 UTF-8 기준 72바이트 이하여야 해요.'),
    confirmPassword: z.string().optional(),
  }).superRefine((values, context) => {
    if (!signingUp) return
    if (!values.name) context.addIssue({ code: 'custom', path: ['name'], message: '이름을 입력해 주세요.' })
    if (values.password !== values.confirmPassword) context.addIssue({ code: 'custom', path: ['confirmPassword'], message: '비밀번호가 일치하지 않아요.' })
  })
  type Values = z.infer<typeof schema>
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({
    resolver: zodResolver(schema), defaultValues: { name: '', email: '', password: '', confirmPassword: '' },
  })

  async function submit(values: Values) {
    setError('')
    try {
      if (signingUp) {
        await signup({ name: values.name!.trim(), email: values.email, password: values.password })
        router.replace('/login?registered=1')
      } else {
        const result = await login({ email: values.email, password: values.password })
        signIn(result.accessToken)
        router.replace('/')
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : '요청에 실패했습니다. 다시 시도해 주세요.')
    }
  }

  if (USE_MOCK) return <main className="mx-auto p-6">데모 모드에서는 사용자 선택을 이용해 주세요. <Link href="/" className="underline">홈으로</Link></main>
  const fields = [
    ...(signingUp ? [{ key: 'name' as const, label: '이름', type: 'text', complete: 'name' }] : []),
    { key: 'email' as const, label: '이메일', type: 'email', complete: 'email' },
    { key: 'password' as const, label: '비밀번호', type: 'password', complete: signingUp ? 'new-password' : 'current-password' },
    ...(signingUp ? [{ key: 'confirmPassword' as const, label: '비밀번호 확인', type: 'password', complete: 'new-password' }] : []),
  ]
  return <main className="mx-auto w-full max-w-md space-y-6 px-4 py-10">
    <h1 className="text-2xl font-bold">{signingUp ? '회원가입' : '로그인'}</h1>
    {registered && !signingUp && <p role="status" className="text-sm text-emerald-700">회원가입이 완료되었습니다. 로그인해 주세요.</p>}
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      {fields.map(field => <div key={field.key}>
        <Label htmlFor={field.key}>{field.label}</Label>
        <Input id={field.key} type={field.type} autoComplete={field.complete} className="mt-1" {...register(field.key)} aria-invalid={!!errors[field.key]} />
        {errors[field.key] && <p role="alert" className="mt-1 text-sm text-red-600">{errors[field.key]?.message}</p>}
      </div>)}
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? signingUp ? '가입 중...' : '로그인 중...' : signingUp ? '회원가입' : '로그인'}
      </Button>
    </form>
    <p className="text-sm text-slate-600">{signingUp ? '이미 계정이 있나요? ' : '계정이 없나요? '}
      <Link className="underline" href={signingUp ? '/login' : '/signup'}>{signingUp ? '로그인' : '회원가입'}</Link>
    </p>
  </main>
}
