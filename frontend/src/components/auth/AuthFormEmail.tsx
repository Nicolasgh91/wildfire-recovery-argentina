import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Mail } from 'lucide-react'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useNavigate, useLocation } from 'react-router-dom'
import { resolveReturnToPath } from '@/lib/routing'
import { toast } from 'sonner'

type EmailValues = {
  email: string
  password: string
}

export function AuthFormEmail() {
  const { t } = useI18n()
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [isLoading, setIsLoading] = useState(false)

  const schema = z.object({
    email: z.string().email(t('validationInvalidEmail') || 'Email invalido'),
    password: z.string().min(1, t('validationRequired') || 'Campo requerido'),
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EmailValues>({
    resolver: zodResolver(schema),
  })

  const from = resolveReturnToPath(
    (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname,
  )

  const onSubmit = async (values: EmailValues) => {
    setIsLoading(true)
    try {
      await signIn(values.email, values.password)
      navigate(from, { replace: true })
      toast.success(t('loginSuccess') || 'Bienvenido de nuevo.')
    } catch {
      const errorMessage = t('loginInvalid') || 'Credenciales incorrectas'
      toast.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="auth-form-email" noValidate>
      <div className="space-y-2">
        <Label htmlFor="email">{t('email')}</Label>
        <Input id="email" type="email" placeholder="user@example.com" {...register('email')} autoComplete="email" />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">{t('password')}</Label>
        <Input
          id="password"
          type="password"
          placeholder="********"
          {...register('password')}
          autoComplete="current-password"
        />
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>

      <Button type="submit" className="w-full gap-2" disabled={isLoading}>
        {isLoading ? (
          t('loading')
        ) : (
          <>
            <Mail className="h-4 w-4" />
            {t('loginEmail') || 'Ingresar con Correo'}
          </>
        )}
      </Button>
    </form>
  )
}