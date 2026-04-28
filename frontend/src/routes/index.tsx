import { Link, createFileRoute } from '@tanstack/react-router'
import { ArrowRight, BarChart3, Database, Layers, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '#/components/ui/button'
import { useAuth } from '#/features/auth/AuthProvider'

export const Route = createFileRoute('/')({ component: Landing })

function Landing() {
  const { status } = useAuth()
  const ctaTo = status === 'authenticated' ? '/dashboard' : '/register'
  const ctaLabel = status === 'authenticated' ? 'Open dashboard' : 'Create your workspace'

  return (
    <div className="page-wrap">
      <section className="rise-in flex flex-col items-center pt-16 pb-20 text-center md:pt-24">
        <span className="island-kicker mb-4">Oil splitting · KH-weighted</span>
        <h1 className="display-title max-w-3xl text-balance text-4xl font-bold leading-tight text-(--sea-ink) md:text-6xl">
          Allocate production back to the right sand —{' '}
          <span className="text-(--lagoon-deep)">in minutes, not weeks.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-balance text-base leading-relaxed text-(--sea-ink-soft) md:text-lg">
          Upload markers, completions, production, and lumping data. Oil Splitter runs
          the marker-aware splitting algorithm and gives you a clean, exportable
          allocation per sand.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to={ctaTo}>
            <Button size="lg">
              {ctaLabel}
              <ArrowRight size={18} />
            </Button>
          </Link>
          <Link to="/login">
            <Button size="lg" variant="secondary">
              Sign in
            </Button>
          </Link>
        </div>
      </section>

      <section className="grid gap-5 pb-16 md:grid-cols-3">
        <FeatureCard
          icon={<Database size={20} />}
          title="Friendly ingestion"
          description="Paste TSV directly from your spreadsheet, or drop CSV/XLSX files. Sheet auto-detection included."
        />
        <FeatureCard
          icon={<Layers size={20} />}
          title="Smart marker matching"
          description="Top-way / bottom-way detection, first-marker tolerance, and pattern-based gap filling — built in."
        />
        <FeatureCard
          icon={<BarChart3 size={20} />}
          title="KH-weighted splitting"
          description="Allocate Oil, Gas, Water, and Water Injection per sand using KH-weighted distribution. Export to CSV."
        />
      </section>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: ReactNode
  title: string
  description: string
}) {
  return (
    <article className="feature-card rounded-3xl border border-(--line) p-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-2xl bg-(--surface-strong) text-(--lagoon-deep) shadow-[0_1px_0_var(--inset-glint)_inset]">
          {icon}
        </span>
        <Sparkles size={14} className="text-(--palm)" />
      </div>
      <h3 className="display-title text-lg font-bold text-(--sea-ink)">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-(--sea-ink-soft)">
        {description}
      </p>
    </article>
  )
}
