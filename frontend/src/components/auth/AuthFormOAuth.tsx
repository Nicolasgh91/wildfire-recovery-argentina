import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useLocation } from 'react-router-dom'
import { resolveReturnToPath, setAuthReturnTo } from '@/lib/routing'
import { toast } from 'sonner'

export function AuthFormOAuth() {
  const { t } = useI18n()
  const { signInWithGoogle } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const location = useLocation()

  const from = resolveReturnToPath(
    (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname,
  )

  const handleGoogleSignIn = async () => {
    setIsLoading(true)
    try {
      setAuthReturnTo(from)
      await signInWithGoogle()
    } catch {
      const message = t('loginInvalid') || 'No se pudo completar la autenticacion con Google. Intenta de nuevo.'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-4" data-testid="auth-form-oauth">
      <Button
        type="button"
        variant="outline"
        className="w-full gap-2"
        onClick={handleGoogleSignIn}
        disabled={isLoading}
        aria-label={t('loginGoogle') || 'Continuar con Google'}
        data-testid="login-google"
      >
        <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M23.22 12.27c0-.85-.08-1.48-.21-2.14H12v4.05h6.42c-.13 1.05-.84 2.63-2.42 3.69l-.02.14 3.49 2.71.24.02c2.19-2.02 3.51-4.99 3.51-8.47Z"
          />
          <path
            fill="#34A853"
            d="M12 23c3.24 0 5.95-1.07 7.94-2.91l-3.78-2.93c-1.01.7-2.36 1.19-4.16 1.19-3.18 0-5.88-2.02-6.84-4.82l-.14.01-3.63 2.81-.05.13C3.32 20.68 7.32 23 12 23Z"
          />
          <path
            fill="#FBBC05"
            d="M5.16 13.53A6.99 6.99 0 0 1 4.77 12c0-.53.09-1.04.23-1.53l-.01-.1-3.68-2.85-.12.06A11.97 11.97 0 0 0 0 12c0 1.94.47 3.78 1.3 5.41l3.86-2.88Z"
          />
          <path
            fill="#EA4335"
            d="M12 4.62c2.31 0 3.87 1 4.75 1.84l3.46-3.38C17.95.94 15.24 0 12 0 7.32 0 3.32 2.31 1.19 6.59l3.8 2.88C6.13 6.64 8.82 4.62 12 4.62Z"
          />
        </svg>
        {isLoading ? t('loading') || 'Cargando...' : t('loginGoogle') || 'Continuar con Google'}
      </Button>
    </div>
  )
}
