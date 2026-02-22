import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // Base
        'w-full px-4 py-3 rounded-lg transition-all duration-200',
        // Background & border (light, premium feel)
        'bg-gray-50 border border-gray-200',
        // Text and placeholder
        'text-base text-foreground placeholder:text-gray-400 md:text-sm',
        // Focus state (visible for accessibility)
        'focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500',
        // Invalid state
        'aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
        // Disabled
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        // Dark mode adjustments
        'dark:bg-input/30 dark:border-input',
        // File input styles
        'file:text-foreground file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium',
        // Selection
        'selection:bg-primary selection:text-primary-foreground',
        className
      )}
      {...props}
    />
  )
}

export { Input }
