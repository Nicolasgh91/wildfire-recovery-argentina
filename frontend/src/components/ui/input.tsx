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
        // Background & border (solid, high contrast)
        'bg-white text-slate-900 border-slate-300 placeholder:text-slate-400',
        // Dark mode adjustments
        'dark:bg-[#1E1E1E] dark:text-white dark:border-slate-700 dark:placeholder:text-slate-500',
        // Text size
        'text-base md:text-sm',
        // Focus state (visible for accessibility)
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        // Invalid state
        'aria-invalid:ring-destructive aria-invalid:border-destructive',
        // Disabled
        'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
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
