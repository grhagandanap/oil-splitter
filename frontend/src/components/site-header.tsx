import { Link } from '@tanstack/react-router'
import { Droplets } from 'lucide-react'

import { useAuth } from '#/features/auth/AuthProvider'

import { Button } from './ui/button'

export function SiteHeader() {
  const { user, status, logout } = useAuth()
  const isAuthed = status === 'authenticated' && user

  return (
    <header className="site-header sticky top-0 z-30 border-b border-(--line)/60 bg-(--header-bg) backdrop-blur-md">
      <div className="page-wrap flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <span
            className="grid h-9 w-9 place-items-center rounded-2xl text-white shadow-[0_8px_18px_rgba(50,143,151,0.28)]"
            style={{
              background:
                'linear-gradient(135deg, var(--lagoon) 0%, var(--lagoon-deep) 60%, var(--palm) 100%)',
            }}
          >
            <Droplets size={18} strokeWidth={2.4} />
          </span>
          <span className="display-title text-lg font-bold tracking-tight text-(--sea-ink)">
            Oil Splitter
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium md:flex">
          {isAuthed ? (
            <Link to="/dashboard" className="nav-link no-underline">
              Dashboard
            </Link>
          ) : null}
        </nav>

        <div className="flex items-center gap-3">
          {isAuthed ? (
            <>
              <span className="hidden text-sm text-(--sea-ink-soft) sm:block">
                {user.full_name ?? user.email}
              </span>
              <Button size="sm" variant="secondary" onClick={() => logout()}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="nav-link hidden text-sm font-medium no-underline sm:block"
              >
                Sign in
              </Link>
              <Link to="/register">
                <Button size="sm">Get started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
