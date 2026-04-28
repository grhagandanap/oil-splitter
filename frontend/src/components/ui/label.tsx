import type { LabelHTMLAttributes } from 'react'

import { cn } from '#/lib/utils'

export function Label({
  className,
  ...rest
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn(
        'text-[12px] font-semibold uppercase tracking-[0.14em] text-(--sea-ink-soft)',
        className,
      )}
      {...rest}
    />
  )
}
