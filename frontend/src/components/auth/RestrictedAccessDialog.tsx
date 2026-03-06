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
  criticalDialogIconClasses,
  criticalDialogIconWrapperClasses,
  criticalDialogPrimaryButtonClasses,
  criticalDialogSecondaryButtonClasses,
  criticalDialogTitleClasses,
} from '@/components/ui/critical-dialog-styles'
import { useI18n } from '@/context/LanguageContext'
import { Z_INDEX } from '@/features/navigation/config/z-index'
import { LockKeyhole } from 'lucide-react'

interface RestrictedAccessDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onGoBack: () => void
  onLogin: () => void
}

export function RestrictedAccessDialog({
  open,
  onOpenChange,
  onGoBack,
  onLogin,
}: RestrictedAccessDialogProps) {
  const { t } = useI18n()

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent
        style={{ zIndex: Z_INDEX.MODAL_CRITICAL }}
        className={criticalDialogContentClasses}
      >
        <AlertDialogHeader>
          <div className="mb-2 flex justify-center">
            <div className={criticalDialogIconWrapperClasses}>
              <LockKeyhole className={criticalDialogIconClasses} />
            </div>
          </div>
          <AlertDialogTitle className={criticalDialogTitleClasses}>
            {t('protectedPageTitle')}
          </AlertDialogTitle>
          <AlertDialogDescription className={criticalDialogDescriptionClasses}>
            {t('protectedPageMessage')}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="sm:justify-center gap-2">
          <AlertDialogCancel onClick={onGoBack} className={criticalDialogSecondaryButtonClasses}>
            {t('goBack')}
          </AlertDialogCancel>
          <AlertDialogAction onClick={onLogin} className={criticalDialogPrimaryButtonClasses}>
            {t('login')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
