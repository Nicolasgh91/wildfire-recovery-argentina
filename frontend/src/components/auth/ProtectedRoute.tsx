import { Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'
import { useI18n } from '@/context/LanguageContext'
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

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'admin' | 'user'
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { status, role } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useI18n()

  if (status === 'loading') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <div className="min-h-screen bg-background">
        <AlertDialog open={true}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('protectedPageTitle')}</AlertDialogTitle>
              <AlertDialogDescription>
                {t('protectedPageMessage')}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => navigate(-1)}>
                {t('goBack')}
              </AlertDialogCancel>
              <AlertDialogAction onClick={() => navigate(LOGIN_PATH, { state: { from: location } })}>
                {t('login')}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    )
  }

  if (requiredRole && role !== requiredRole && role !== 'admin') {
    return <Navigate to={HOME_PATH} replace />
  }

  return <>{children}</>
}
