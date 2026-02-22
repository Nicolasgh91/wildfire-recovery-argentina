import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, AlertTriangle } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { LOGIN_PATH, clearAuthReturnTo, consumeAuthReturnTo } from '@/lib/routing'

const SOFT_TIMEOUT_MS = 10_000
const HARD_TIMEOUT_MS = 20_000
const TRANSIENT_ERROR_CODES = new Set(['server_error', 'temporarily_unavailable'])

type CallbackErrorState = {
  code: string | null
  message: string
  isTransient: boolean
}

function parseUrlAuthError(): CallbackErrorState | null {
  const searchParams = new URLSearchParams(window.location.search)
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))

  const errorCode =
    searchParams.get('error') ??
    hashParams.get('error') ??
    searchParams.get('error_code') ??
    hashParams.get('error_code')

  const errorDescription = searchParams.get('error_description') ?? hashParams.get('error_description')

  if (!errorCode && !errorDescription) {
    return null
  }

  const normalizedCode = (errorCode || '').toLowerCase()
  const isTransient = !normalizedCode || TRANSIENT_ERROR_CODES.has(normalizedCode)

  return {
    code: normalizedCode || null,
    message:
      errorDescription ||
      (isTransient
        ? 'No pudimos completar el login por un problema temporal. Intenta nuevamente.'
        : 'No se pudo completar el login. Intenta iniciar sesion nuevamente.'),
    isTransient,
  }
}

export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const [errorState, setErrorState] = useState<CallbackErrorState | null>(null)
  const [statusMessage, setStatusMessage] = useState('Completando autenticacion...')
  const [retryAttempt, setRetryAttempt] = useState(0)

  useEffect(() => {
    let isActive = true
    let didComplete = false

    const completeWithError = (nextError: CallbackErrorState) => {
      if (!isActive || didComplete) return
      didComplete = true
      clearAuthReturnTo()
      setErrorState(nextError)
    }

    const completeWithSuccess = () => {
      if (!isActive || didComplete) return
      didComplete = true
      navigate(consumeAuthReturnTo(), { replace: true })
    }

    const urlError = parseUrlAuthError()
    if (urlError) {
      if (urlError.code === 'access_denied') {
        clearAuthReturnTo()
        navigate(LOGIN_PATH, { replace: true, state: { cancelled: true } })
        return () => {
          isActive = false
        }
      }
      completeWithError(urlError)
      return () => {
        isActive = false
      }
    }

    const softTimeout = setTimeout(() => {
      if (!isActive || didComplete) return
      setStatusMessage('Todavia estamos procesando el inicio de sesion...')
    }, SOFT_TIMEOUT_MS)

    const hardTimeout = setTimeout(() => {
      completeWithError({
        code: null,
        message: 'La autenticacion esta demorando mas de lo esperado. Intenta nuevamente.',
        isTransient: true,
      })
    }, HARD_TIMEOUT_MS)

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!isActive || didComplete) return
      if (session) {
        completeWithSuccess()
      }
    })

    void supabase.auth
      .getSession()
      .then(({ data: sessionData, error }) => {
        if (!isActive || didComplete) return

        if (error) {
          completeWithError({
            code: null,
            message: 'No pudimos validar la sesion. Intenta nuevamente.',
            isTransient: true,
          })
          return
        }

        if (sessionData.session) {
          completeWithSuccess()
        }
      })
      .catch(() => {
        completeWithError({
          code: null,
          message: 'No pudimos validar la sesion. Intenta nuevamente.',
          isTransient: true,
        })
      })

    return () => {
      isActive = false
      clearTimeout(softTimeout)
      clearTimeout(hardTimeout)
      data.subscription.unsubscribe()
    }
  }, [navigate, retryAttempt])

  if (errorState) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6 text-center">
        <AlertTriangle className="h-10 w-10 text-destructive" />
        <h1 className="text-2xl font-semibold">No se pudo completar el login</h1>
        <p className="text-sm text-muted-foreground">{errorState.message}</p>
        <div className="flex gap-2">
          {errorState.isTransient && (
            <Button
              variant="outline"
              onClick={() => {
                setErrorState(null)
                setStatusMessage('Completando autenticacion...')
                setRetryAttempt((attempt) => attempt + 1)
              }}
            >
              Reintentar
            </Button>
          )}
          <Button onClick={() => navigate(LOGIN_PATH, { replace: true })}>Ir a login</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">{statusMessage}</p>
    </div>
  )
}
