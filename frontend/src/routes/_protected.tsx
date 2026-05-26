import { createFileRoute, redirect, Outlet, Link, useNavigate } from '@tanstack/react-router'
import { useAuth } from '#/contexts/auth'
import { Button } from '#/components/ui/button'

export const Route = createFileRoute('/_protected')({
  beforeLoad: () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (!token) {
      throw redirect({ to: '/login' })
    }
  },
  component: ProtectedLayout,
})

function ProtectedLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate({ to: '/login' })
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 flex flex-col border-r border-[var(--line)] bg-[var(--surface)] backdrop-blur-sm">
        <div className="px-5 py-5 border-b border-[var(--line)]">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-gradient-to-br from-[var(--lagoon)] to-[var(--palm)] flex items-center justify-center shadow-sm shrink-0">
              <svg
                className="size-4 text-white"
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
            <div>
              <p className="display-title text-sm font-bold text-[var(--sea-ink)] leading-none">
                Oil Splitter
              </p>
              <p className="island-kicker text-[0.6rem] mt-0.5 opacity-70">Analytics</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          <NavItem
            to="/dashboard"
            label="Dashboard"
            icon={
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
              </svg>
            }
          />
          <NavItem
            to="/dashboard"
            label="New Project"
            icon={
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            }
          />

          <div className="pt-3 pb-1">
            <p className="island-kicker px-2 text-[0.6rem] opacity-50">History</p>
          </div>
          <NavItem
            to="/dashboard"
            label="All Projects"
            icon={
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        </nav>

        <div className="px-3 py-4 border-t border-[var(--line)]">
          <div className="px-2 py-2 rounded-lg bg-[var(--sand)] mb-2">
            <p className="text-xs font-medium text-[var(--sea-ink)] truncate">
              {user?.email ?? '…'}
            </p>
            <p className="text-[0.65rem] text-[var(--sea-ink-soft)] mt-0.5">Petroleum Engineer</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-[var(--sea-ink-soft)] hover:text-destructive hover:bg-destructive/10"
            onClick={handleLogout}
          >
            <svg className="size-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
            </svg>
            Sign Out
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({
  to,
  label,
  icon,
}: {
  to: string
  label: string
  icon: React.ReactNode
}) {
  return (
    <Link
      to={to as '/dashboard'}
      className="flex items-center gap-2.5 px-2 py-2 rounded-md text-sm font-medium text-[var(--sea-ink-soft)] hover:bg-[var(--link-bg-hover)] hover:text-[var(--sea-ink)] transition-colors"
      activeProps={{ className: 'bg-[var(--link-bg-hover)] text-[var(--sea-ink)]' }}
    >
      {icon}
      {label}
    </Link>
  )
}
