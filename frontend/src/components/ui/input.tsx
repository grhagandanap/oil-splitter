import { forwardRef, type InputHTMLAttributes } from 'react'

import { cn } from '#/lib/utils'

type Props = InputHTMLAttributes<HTMLInputElement>

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        'h-11 w-full rounded-xl border border-(--line) bg-white/85 px-4 text-[15px] text-(--sea-ink)',
        'placeholder:text-(--sea-ink-soft) shadow-[inset_0_1px_0_var(--inset-glint)]',
        'focus:border-(--lagoon-deep) focus:outline-none focus:ring-2 focus:ring-(--lagoon)',
        'disabled:cursor-not-allowed disabled:opacity-70',
        className,
      )}
      {...rest}
    />
  )
})
