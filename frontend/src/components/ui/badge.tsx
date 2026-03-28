import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-white shadow hover:bg-primary/80",
        secondary: "border-transparent bg-white/10 text-white hover:bg-white/20",
        destructive: "border-transparent bg-red-500 text-white shadow hover:bg-red-500/80",
        outline: "border-white/10 text-slate-300",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
