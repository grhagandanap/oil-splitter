type Props = {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes: Record<NonNullable<Props['size']>, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
}

export function Spinner({ size = 'md', className }: Props) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block animate-spin rounded-full border-(--lagoon-deep)/30 border-t-(--lagoon-deep) ${sizes[size]} ${className ?? ''}`}
    />
  )
}
