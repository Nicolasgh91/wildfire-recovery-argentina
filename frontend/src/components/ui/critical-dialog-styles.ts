/**
 * Shared styles for critical modals (RestrictedAccessDialog, ExternalConfirmDialog, Terms of use).
 * Uses CSS variables --critical-dialog-* from index.css so one change updates all modals.
 */

export const criticalDialogContentClasses =
  'border-none shadow-2xl backdrop-blur-sm bg-critical-dialog/[0.79] text-critical-dialog-foreground dark:bg-critical-dialog dark:backdrop-blur-none'

export const criticalDialogTitleClasses = 'text-center text-critical-dialog-foreground'

export const criticalDialogDescriptionClasses = 'text-center text-critical-dialog-muted'

export const criticalDialogIconWrapperClasses = 'rounded-full bg-critical-dialog-foreground/10 p-3'

export const criticalDialogIconClasses = 'h-6 w-6 text-critical-dialog-foreground'

/** Secondary action (Cancel / Volver) */
export const criticalDialogSecondaryButtonClasses =
  'border-critical-dialog-foreground/30 bg-critical-dialog-foreground/10 text-critical-dialog-foreground hover:bg-critical-dialog-foreground/20 hover:text-critical-dialog-foreground dark:border-border dark:bg-secondary dark:text-foreground dark:hover:bg-secondary/80'

/** Primary action (Continue / Login) */
export const criticalDialogPrimaryButtonClasses =
  'bg-white text-footer hover:bg-white/90 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90'
