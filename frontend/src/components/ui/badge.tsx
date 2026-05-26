import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "#/lib/utils.ts"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-white",
        outline: "text-foreground",
        success:
          "border-transparent bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400",
        warning:
          "border-transparent bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400",
        processing:
          "border-transparent bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof badgeVariants>) {
  return (
    <div
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
