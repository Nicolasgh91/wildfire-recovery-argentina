import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, AlertTriangle } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { setAuthToken } from '@/services/api'
import { Button } from '@/components/ui/button'

export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    let active = true

    const completeAuth = async () => {
      try {
        const code = searchParams.get('code')
        const { data: existing } = await supabase.auth.getSession()

        if (!existing.session && code) {
          const { data, error } = await supabase.auth.exchangeCodeForSession(code)
          if (error) throw error
          setAuthToken(data.session?.access_token ?? null)
        } else {
          setAuthToken(existing.session?.access_token ?? null)
        }

        const returnTo = sessionStorage.getItem('auth:returnTo') || '/'
        sessionStorage.removeItem('auth:returnTo')

        if (active) {
          navigate(returnTo, { replace: true })
        }
      } catch {
        if (active) {
          setHasError(true)
        }
      }
    }

    void completeAuth()

    return () => {
      active = false
    }
  }, [navigate, searchParams])

  if (hasError) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6 text-center">
        <AlertTriangle className="h-10 w-10 text-destructive" />
        <h1 className="text-2xl font-semibold">No se pudo completar el login</h1>
        <p className="text-sm text-muted-foreground">
          Intenta iniciar sesion nuevamente.
        </p>
        <Button onClick={() => navigate('/login', { replace: true })}>Ir a login</Button>
      </div>
    )
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 p-6 text-center">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Completando autenticacion...</p>
    </div>
  )
}
