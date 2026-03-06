import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  criticalDialogContentClasses,
  criticalDialogDescriptionClasses,
  criticalDialogPrimaryButtonClasses,
  criticalDialogSecondaryButtonClasses,
  criticalDialogTitleClasses,
} from '@/components/ui/critical-dialog-styles'
import { useI18n } from '@/context/LanguageContext'
import { Z_INDEX } from '@/features/navigation/config/z-index'

interface ExternalConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  href: string
  siteName: string
}

export function ExternalConfirmDialog({
  open,
  onOpenChange,
  href,
  siteName,
}: ExternalConfirmDialogProps) {
  const { t } = useI18n()

  const handleContinue = () => {
    if (!href) return
    window.open(href, '_blank', 'noopener,noreferrer')
    onOpenChange(false)
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent
        style={{ zIndex: Z_INDEX.MODAL_CRITICAL }}
        className={criticalDialogContentClasses}
      >
        <AlertDialogHeader>
          <AlertDialogTitle className={criticalDialogTitleClasses}>
            {t('footerLeavingTitle')}
          </AlertDialogTitle>
          <AlertDialogDescription className={criticalDialogDescriptionClasses}>
            {t('footerLeavingDescription')}
            {siteName ? ` ${siteName}` : ''}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="sm:justify-center gap-2">
          <AlertDialogCancel className={criticalDialogSecondaryButtonClasses}>
            {t('footerCancel')}
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleContinue} className={criticalDialogPrimaryButtonClasses}>
            {t('footerContinue')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

