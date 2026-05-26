import { createFileRoute } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { useAuth } from '#/contexts/auth'

export const Route = createFileRoute('/_protected/dashboard')({
  component: DashboardPage,
})

function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="px-8 py-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="island-kicker mb-1">Welcome back</p>
          <h2 className="display-title text-2xl font-bold text-[var(--sea-ink)]">
            {user?.email?.split('@')[0] ?? 'Engineer'}
          </h2>
          <p className="text-sm text-[var(--sea-ink-soft)] mt-0.5">
            Manage your marker allocation and splitting projects
          </p>
        </div>
        <Button className="bg-gradient-to-r from-[var(--lagoon)] to-[var(--palm)] text-white border-0 hover:opacity-90 shadow-sm">
          <svg className="size-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Project
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Total Projects"
          value="0"
          icon={
            <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
            </svg>
          }
        />
        <StatCard
          label="Completed Runs"
          value="0"
          icon={
            <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Wells Processed"
          value="0"
          icon={
            <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15M14.25 3.104c.251.023.501.05.75.082" />
            </svg>
          }
        />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-[var(--sea-ink)] mb-4">Recent Projects</h3>
        <EmptyState />
      </div>
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <Card className="island-shell border-[var(--line)] gap-3">
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between">
          <CardDescription className="text-xs">{label}</CardDescription>
          <span className="text-[var(--lagoon)] opacity-70">{icon}</span>
        </div>
        <CardTitle className="text-3xl font-bold text-[var(--sea-ink)]">{value}</CardTitle>
      </CardHeader>
    </Card>
  )
}

function EmptyState() {
  return (
    <div className="island-shell border-[var(--line)] rounded-xl p-12 text-center">
      <div className="inline-flex items-center justify-center size-14 rounded-full bg-[var(--sand)] mb-4">
        <svg
          className="size-7 text-[var(--lagoon)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.4}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>
      <h4 className="display-title text-lg font-semibold text-[var(--sea-ink)] mb-1">
        No projects yet
      </h4>
      <p className="text-sm text-[var(--sea-ink-soft)] max-w-sm mx-auto mb-5">
        Create your first project by uploading your marker, well, production, completion,
        and lumping datasets.
      </p>
      <Button
        size="sm"
        className="bg-gradient-to-r from-[var(--lagoon)] to-[var(--palm)] text-white border-0 hover:opacity-90"
      >
        <svg className="size-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Create First Project
      </Button>
    </div>
  )
}
