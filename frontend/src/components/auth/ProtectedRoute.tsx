import { Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'
import { RestrictedAccessDialog } from '@/components/auth/RestrictedAccessDialog'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'admin' | 'user'
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { status, role } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

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
        <RestrictedAccessDialog
          open
          onOpenChange={() => undefined}
          onGoBack={() => navigate(-1)}
          onLogin={() => navigate(LOGIN_PATH, { state: { from: location } })}
        />
      </div>
    )
  }

  if (requiredRole && role !== requiredRole && role !== 'admin') {
    return <Navigate to={HOME_PATH} replace />
  }

  return <>{children}</>
}
