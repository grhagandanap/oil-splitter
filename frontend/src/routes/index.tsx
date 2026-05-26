import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

export const Route = createFileRoute('/')({
  component: IndexPage,
})

function IndexPage() {
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    navigate({ to: token ? '/dashboard' : '/login', replace: true })
  }, [navigate])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-sm text-[var(--sea-ink-soft)]">Loading…</div>
    </div>
  )
}
