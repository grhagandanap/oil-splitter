import type { ReactNode } from 'react'

import { cn } from '#/lib/utils'

export type TabItem<T extends string> = {
  value: T
  label: string
  icon?: ReactNode
  badge?: ReactNode
}

type Props<T extends string> = {
  items: TabItem<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
  variant?: 'pill' | 'underline'
}

export function Tabs<T extends string>({
  items,
  value,
  onChange,
  className,
  variant = 'pill',
}: Props<T>) {
  if (variant === 'underline') {
    return (
      <div
        role="tablist"
        className={cn(
          'flex flex-wrap items-center gap-6 border-b border-(--line)/70',
          className,
        )}
      >
        {items.map((item) => {
          const active = item.value === value
          return (
            <button
              key={item.value}
              role="tab"
              type="button"
              aria-selected={active}
              onClick={() => onChange(item.value)}
              className={cn(
                'relative flex items-center gap-2 pb-3 text-sm font-semibold transition-colors',
                active ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft) hover:text-(--sea-ink)',
              )}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge}
              {active ? (
                <span className="absolute -bottom-px left-0 right-0 h-0.5 rounded-full bg-(--lagoon-deep)" />
              ) : null}
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex flex-wrap items-center gap-1 rounded-2xl border border-(--line)/70 bg-(--surface) p-1 shadow-[inset_0_1px_0_var(--inset-glint)]',
        className,
      )}
    >
      {items.map((item) => {
        const active = item.value === value
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cn(
              'flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold tracking-tight transition-all',
              active
                ? 'bg-(--surface-strong) text-(--sea-ink) shadow-[0_4px_12px_rgba(23,58,64,0.08),0_1px_0_var(--inset-glint)_inset]'
                : 'text-(--sea-ink-soft) hover:text-(--sea-ink)',
            )}
          >
            {item.icon}
            <span>{item.label}</span>
            {item.badge}
          </button>
        )
      })}
    </div>
  )
}
