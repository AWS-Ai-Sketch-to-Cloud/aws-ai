'use client'

import { useEffect, useState } from 'react'
import { useToast } from '@/hooks/use-toast'
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast'

function ToastCountdown({
  duration = 5000,
  open = true,
}: {
  duration?: number
  open?: boolean
}) {
  const [secondsLeft, setSecondsLeft] = useState(
    Math.max(1, Math.ceil(duration / 1000)),
  )

  useEffect(() => {
    if (!open) {
      return
    }

    setSecondsLeft(Math.max(1, Math.ceil(duration / 1000)))

    const startedAt = Date.now()
    const interval = window.setInterval(() => {
      const elapsed = Date.now() - startedAt
      const remaining = Math.max(0, duration - elapsed)
      const nextSeconds = Math.max(1, Math.ceil(remaining / 1000))

      setSecondsLeft(nextSeconds)

      if (remaining <= 0) {
        window.clearInterval(interval)
      }
    }, 100)

    return () => window.clearInterval(interval)
  }, [duration, open])

  return <div className="text-xs font-medium opacity-75">{secondsLeft}초</div>
}

function ToastAutoDismiss({
  id,
  duration = 5000,
  open = true,
}: {
  id: string
  duration?: number
  open?: boolean
}) {
  const { dismiss } = useToast()

  useEffect(() => {
    if (!open) {
      return
    }

    const timeout = window.setTimeout(() => {
      dismiss(id)
    }, duration)

    return () => window.clearTimeout(timeout)
  }, [dismiss, duration, id, open])

  return null
}

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({
        id,
        title,
        description,
        action,
        duration = 5000,
        variant,
        open,
        ...props
      }) {
        return (
          <Toast
            key={id}
            duration={duration}
            variant={variant}
            open={open}
            {...props}
          >
            <ToastAutoDismiss id={id} duration={duration} open={open} />
            <div className="grid flex-1 gap-1 pr-16">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            <div className="absolute right-10 top-3">
              <ToastCountdown duration={duration} open={open} />
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
