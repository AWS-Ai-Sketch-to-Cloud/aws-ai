import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-2xl text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/25 aria-invalid:ring-destructive/20",
  {
    variants: {
      variant: {
        default:
          'bg-[#122033] text-white shadow-[0_18px_40px_rgba(18,32,51,0.18)] hover:-translate-y-0.5 hover:bg-[#1a2c45]',
        destructive:
          'bg-destructive text-white shadow-[0_18px_40px_rgba(220,38,38,0.18)] hover:-translate-y-0.5 hover:bg-destructive/90',
        outline:
          'border border-[#d9e4f2] bg-white text-[#314257] shadow-[0_10px_24px_rgba(72,123,255,0.08)] hover:-translate-y-0.5 hover:border-[#487bff] hover:text-[#122033]',
        secondary:
          'bg-[#edf4ff] text-[#2f64ef] shadow-[0_10px_24px_rgba(72,123,255,0.08)] hover:-translate-y-0.5 hover:bg-[#dfeaff]',
        ghost:
          'text-[#52627a] hover:bg-white hover:text-[#122033]',
        link: 'text-[#487bff] underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-11 px-5 py-2.5 has-[>svg]:px-4',
        sm: 'h-9 rounded-xl gap-1.5 px-3.5 has-[>svg]:px-3',
        lg: 'h-12 rounded-2xl px-6 has-[>svg]:px-5',
        icon: 'size-11',
        'icon-sm': 'size-9',
        'icon-lg': 'size-12',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
