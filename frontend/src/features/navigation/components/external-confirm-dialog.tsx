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
      <AlertDialogContent style={{ zIndex: Z_INDEX.MODAL_CRITICAL }}>
        <AlertDialogHeader>
          <AlertDialogTitle>{t('footerLeavingTitle')}</AlertDialogTitle>
          <AlertDialogDescription>
            {t('footerLeavingDescription')}
            {siteName ? ` ${siteName}` : ''}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t('footerCancel')}</AlertDialogCancel>
          <AlertDialogAction onClick={handleContinue}>{t('footerContinue')}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

