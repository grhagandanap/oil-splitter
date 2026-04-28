import { Link, createFileRoute, useNavigate } from '@tanstack/react-router'
import { type FormEvent, useEffect, useState } from 'react'

import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { useAuth } from '#/features/auth/AuthProvider'
import { readErrorMessage } from '#/lib/api'

export const Route = createFileRoute('/login')({ component: LoginPage })

function LoginPage() {
  const navigate = useNavigate()
  const { login, status } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (status === 'authenticated') {
      void navigate({ to: '/dashboard', replace: true })
    }
  }, [status, navigate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login({ email, password })
      void navigate({ to: '/dashboard', replace: true })
    } catch (err) {
      setError(await readErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-wrap flex min-h-[calc(100vh-12rem)] items-center justify-center py-12">
      <div className="rise-in island-shell w-full max-w-md rounded-3xl p-8">
        <div className="mb-7 text-center">
          <span className="island-kicker">Welcome back</span>
          <h1 className="display-title mt-2 text-2xl font-bold text-(--sea-ink)">
            Sign in to Oil Splitter
          </h1>
          <p className="mt-2 text-sm text-(--sea-ink-soft)">
            Pick up where you left off — your projects are waiting.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </div>
          ) : null}

          <Button type="submit" className="w-full" isLoading={submitting} size="lg">
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-(--sea-ink-soft)">
          New to Oil Splitter?{' '}
          <Link
            to="/register"
            className="font-semibold text-(--lagoon-deep) no-underline hover:text-[#246f76]"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
