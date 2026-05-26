import { createFileRoute, redirect, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { useAuth } from '#/contexts/auth'

export const Route = createFileRoute('/login')({
  beforeLoad: () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (token) throw redirect({ to: '/dashboard' })
  },
  component: LoginPage,
})

function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(email, password)
      navigate({ to: '/dashboard' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid credentials')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm rise-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center size-12 rounded-xl bg-gradient-to-br from-[var(--lagoon)] to-[var(--palm)] mb-4 shadow-lg">
            <svg
              className="size-6 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15M14.25 3.104c.251.023.501.05.75.082M19.8 15l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.607L5 14.5m14.8.5l1.196 3.274A2.25 2.25 0 0118.866 21H5.134a2.25 2.25 0 01-2.13-2.726L4.196 15M5 14.5l-1.196.393"
              />
            </svg>
          </div>
          <h1 className="display-title text-2xl font-bold text-[var(--sea-ink)]">
            Oil Splitter
          </h1>
          <p className="text-sm text-[var(--sea-ink-soft)] mt-1">
            Petroleum Data Analytics Platform
          </p>
        </div>

        <Card className="island-shell border-[var(--line)]">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Sign In</CardTitle>
            <CardDescription>Access your engineering workspace</CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md px-3 py-2">
                  {error}
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="engineer@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Signing in…' : 'Sign In'}
              </Button>
            </form>
          </CardContent>

          <CardFooter className="justify-center pt-0">
            <p className="text-sm text-muted-foreground">
              No account?{' '}
              <Link to="/register" className="font-medium text-[var(--lagoon-deep)] hover:underline">
                Create one
              </Link>
            </p>
          </CardFooter>
        </Card>

        <p className="text-center text-xs text-[var(--sea-ink-soft)] mt-6 opacity-60">
          For authorized petroleum engineers only
        </p>
      </div>
    </div>
  )
}
