import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Mail } from 'lucide-react'
import { useI18n } from '@/context/LanguageContext'
import { toast } from 'sonner'
import { useAuth } from '@/context/AuthContext'
import { resolveReturnToPath, setAuthReturnTo } from '@/lib/routing'

type OTPValues = {
  email: string
}

export function AuthFormOTP() {
  const { t } = useI18n()
  const { signInWithOtp } = useAuth()
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const location = useLocation()

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown((currentCooldown) => currentCooldown - 1), 1000)
    }
    return () => clearTimeout(timer)
  }, [cooldown])

  const schema = z.object({
    email: z.string().email(t('validationInvalidEmail') || 'Email invalido'),
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<OTPValues>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (values: OTPValues) => {
    setError('')
    setSuccess('')

    const from = resolveReturnToPath(
      (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname,
    )
    setAuthReturnTo(from)

    setIsLoading(true)
    try {
      await signInWithOtp(values.email)
      const message = `Revisa tu bandeja de entrada. Hemos enviado un enlace a ${values.email}`
      setSuccess(message)
      setCooldown(60)
      toast.success(message)
    } catch (err: any) {
      if (err?.status === 429) {
        setError('Demasiados intentos. Por favor espera y vuelve a intentarlo mas tarde.')
      } else {
        setError(err?.message || 'Ocurrio un error inesperado al enviar el enlace.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="auth-form-otp" noValidate>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success ? (
        <div className="space-y-4">
          <Alert>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => handleSubmit(onSubmit)()}
            disabled={cooldown > 0 || isLoading}
          >
            {cooldown > 0 ? `Reenviar enlace en ${cooldown}s` : 'Reenviar enlace'}
          </Button>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <Label htmlFor="otp-email">{t('email')}</Label>
            <Input id="otp-email" type="email" placeholder="user@example.com" {...register('email')} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>

          <Button type="submit" className="w-full gap-2" disabled={isLoading}>
            {isLoading ? (
              t('loading')
            ) : (
              <>
                <Mail className="h-4 w-4" />
                Enviar enlace de acceso unico
              </>
            )}
          </Button>
        </>
      )}
    </form>
  )
}