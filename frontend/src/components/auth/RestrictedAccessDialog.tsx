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
import { useI18n } from '@/context/LanguageContext'
import { Z_INDEX } from '@/features/navigation/config/z-index'

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
      <AlertDialogContent style={{ zIndex: Z_INDEX.MODAL_CRITICAL }}>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('protectedPageTitle')}</AlertDialogTitle>
          <AlertDialogDescription>{t('protectedPageMessage')}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onGoBack}>{t('goBack')}</AlertDialogCancel>
          <AlertDialogAction onClick={onLogin}>{t('login')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
