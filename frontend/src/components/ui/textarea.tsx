import { forwardRef, type TextareaHTMLAttributes } from 'react'

import { cn } from '#/lib/utils'

type Props = TextareaHTMLAttributes<HTMLTextAreaElement>

export const Textarea = forwardRef<HTMLTextAreaElement, Props>(function Textarea(
  { className, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(
        'min-h-32 w-full rounded-xl border border-(--line) bg-white/85 px-4 py-3 text-[14px] leading-relaxed text-(--sea-ink)',
        'placeholder:text-(--sea-ink-soft) shadow-[inset_0_1px_0_var(--inset-glint)]',
        'focus:border-(--lagoon-deep) focus:outline-none focus:ring-2 focus:ring-(--lagoon)',
        'disabled:cursor-not-allowed disabled:opacity-70',
        'font-mono',
        className,
      )}
      {...rest}
    />
  )
})
