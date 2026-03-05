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
        style={{ zIndex: Z_INDEX.MODAL_CRITICAL, backgroundColor: 'hsl(164deg 86% 16% / 79%)' }}
        className="border-none shadow-2xl backdrop-blur-sm dark:bg-card dark:backdrop-blur-none"
      >
        <AlertDialogHeader>
          <div className="mb-2 flex justify-center">
            <div className="rounded-full bg-white/10 p-3">
              <LockKeyhole className="h-6 w-6 text-white dark:text-foreground" />
            </div>
          </div>
          <AlertDialogTitle className="text-center text-white dark:text-foreground">
            {t('protectedPageTitle')}
          </AlertDialogTitle>
          <AlertDialogDescription className="text-center text-white/75 dark:text-muted-foreground">
            {t('protectedPageMessage')}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="sm:justify-center gap-2">
          <AlertDialogCancel
            onClick={onGoBack}
            className="border-white/30 bg-white/10 text-white hover:bg-white/20 hover:text-white dark:border-border dark:bg-secondary dark:text-foreground dark:hover:bg-secondary/80"
          >
            {t('goBack')}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onLogin}
            className="bg-white text-footer hover:bg-white/90 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90"
          >
            {t('login')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
