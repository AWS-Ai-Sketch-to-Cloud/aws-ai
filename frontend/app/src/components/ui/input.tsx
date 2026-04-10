import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'file:text-foreground placeholder:text-[#8a98ab] selection:bg-primary selection:text-primary-foreground h-11 w-full min-w-0 rounded-2xl border border-[#d9e4f2] bg-[#f9fbff] px-4 py-2 text-base text-[#122033] shadow-[0_10px_24px_rgba(72,123,255,0.05)] transition-[color,box-shadow,border-color] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
        'focus-visible:border-[#487bff] focus-visible:ring-[3px] focus-visible:ring-[#487bff]/15',
        'aria-invalid:ring-destructive/20 aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
