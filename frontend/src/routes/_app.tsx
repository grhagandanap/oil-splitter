import { Outlet, createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

import { Spinner } from '#/components/ui/spinner'
import { useAuth } from '#/features/auth/AuthProvider'

export const Route = createFileRoute('/_app')({ component: AppLayout })

function AppLayout() {
  const { status } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (status === 'unauthenticated') {
      void navigate({ to: '/login', replace: true })
    }
  }, [status, navigate])

  if (status !== 'authenticated') {
    return (
      <div className="page-wrap flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-(--sea-ink-soft)">
          <Spinner size="md" />
          <span>Loading your workspace…</span>
        </div>
      </div>
    )
  }

  return <Outlet />
}
