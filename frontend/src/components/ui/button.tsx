import { forwardRef, type ButtonHTMLAttributes } from 'react'

import { cn } from '#/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'destructive'
type Size = 'sm' | 'md' | 'lg'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  isLoading?: boolean
}

const variants: Record<Variant, string> = {
  primary:
    'bg-(--lagoon-deep) text-white shadow-[0_8px_22px_rgba(50,143,151,0.28)] hover:bg-(--lagoon) disabled:bg-(--sea-ink-soft)',
  secondary:
    'border border-(--line) bg-(--surface-strong) text-(--sea-ink) hover:bg-(--link-bg-hover)',
  ghost: 'bg-transparent text-(--sea-ink) hover:bg-(--surface)',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
}

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
}

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { className, variant = 'primary', size = 'md', isLoading, disabled, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl font-semibold tracking-tight transition-all',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--lagoon) focus-visible:ring-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-70',
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
      ) : null}
      {children}
    </button>
  )
})
