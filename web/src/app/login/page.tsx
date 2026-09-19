import AuthForm from '@/components/auth/AuthForm'

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ registered?: string }> }) {
  const params = await searchParams
  return <AuthForm mode="login" registered={params.registered === '1'} />
}
