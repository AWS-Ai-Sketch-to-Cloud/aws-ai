import * as React from 'react'

import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'flex field-sizing-content min-h-20 w-full rounded-[1.5rem] border border-[#d9e4f2] bg-[#f9fbff] px-4 py-3 text-base leading-6 text-[#122033] shadow-[0_10px_24px_rgba(72,123,255,0.05)] transition-[color,box-shadow,border-color] outline-none placeholder:text-[#8a98ab] focus-visible:border-[#487bff] focus-visible:ring-[3px] focus-visible:ring-[#487bff]/15 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:ring-destructive/20 aria-invalid:border-destructive md:text-sm',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
