import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AlertCircle, Mail, Eye, EyeOff, Check, X, User } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import bosqueLanding from '@/assets/bosque_landing.webp'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'
import { resolveReturnToPath, setAuthReturnTo } from '@/lib/routing'
import { toast } from 'sonner'

type RegisterValues = {
  firstName: string
  lastName: string
  email: string
  password: string
  confirmPassword: string
}

function PasswordChecklist({ password = '' }: { password?: string }) {
  const rules = [
    { label: 'Al menos 8 caracteres', test: (v: string) => v.length >= 8 },
    { label: 'Una letra mayúscula y una minúscula', test: (v: string) => /[A-Z]/.test(v) && /[a-z]/.test(v) },
    { label: 'Un número', test: (v: string) => /[0-9]/.test(v) },
    { label: 'Un carácter especial', test: (v: string) => /[^A-Za-z0-9]/.test(v) },
  ]

  return (
    <ul className="mt-2 text-xs space-y-1">
      {rules.map((rule, idx) => {
        const met = rule.test(password)
        return (
          <li key={idx} className={`flex items-center gap-2 ${met ? 'text-primary' : 'text-muted-foreground'}`}>
            {met ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
            <span>{rule.label}</span>
          </li>
        )
      })}
    </ul>
  )
}


export default function RegisterPage() {
  const { t } = useI18n()
  const { signUpWithEmail, signInWithGoogle } = useAuth()
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)
  const location = useLocation()

  const from = resolveReturnToPath(
    (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname,
  )

  const handleGoogleSignIn = async () => {
    setIsGoogleLoading(true)
    try {
      setAuthReturnTo(from)
      await signInWithGoogle()
    } catch {
      const message = t('loginInvalid') || 'No se pudo completar la autenticacion con Google. Intenta de nuevo.'
      toast.error(message)
    } finally {
      setIsGoogleLoading(false)
    }
  }

  const registerSchema = z.object({
    firstName: z.string().min(2, t('validationRequired')).max(50, t('validationMax50')),
    lastName: z.string().min(2, t('validationRequired')).max(50, t('validationMax50')),
    email: z.string().email(t('validationInvalidEmail')),
    password: z.string()
      .min(1, 'La contraseña es obligatoria para crear tu cuenta.')
      .min(8, 'La contraseña es demasiado corta. Necesita al menos 8 caracteres.')
      .refine((val) => /[A-Z]/.test(val) && /[a-z]/.test(val), {
        message: 'La contraseña debe incluir al menos una letra mayúscula y una minúscula.',
      })
      .refine((val) => /[0-9]/.test(val) && /[^A-Za-z0-9]/.test(val), {
        message: 'La contraseña debe incluir al menos un número y un símbolo.',
      }),
    confirmPassword: z.string().min(1, 'Confirmar la contraseña es obligatorio.')
  }).refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas ingresadas no coinciden. Verifícalas usando el icono del ojo.",
    path: ["confirmPassword"],
  })

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const onSubmit = async (values: RegisterValues) => {
    setError('')
    setSuccess('')
    setIsLoading(true)

    try {
      await signUpWithEmail({
        email: values.email,
        password: values.password || undefined,
        options: {
          data: {
            first_name: values.firstName,
            last_name: values.lastName,
          }
        }
      } as any) // Type casting depends on AuthContext actual interface, assuming auth context can handle extra fields.
      setSuccess(t('registerSuccess') || 'Cuenta creada exitosamente')
    } catch {
      setError(t('registerError'))
    }

    setIsLoading(false)
  }

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
  })

  return (
    <div className="relative min-h-screen bg-auth-page p-6 md:p-8">
      <Link to={LOGIN_PATH} className="absolute left-6 top-6 md:left-8 md:top-8">
        <BrandLogo size="md" showName={false} />
      </Link>

      <div className="grid min-h-[calc(100vh-3rem)] grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <div className="flex items-center justify-center">
          <div className="w-full max-w-lg text-left pt-16 lg:pt-0">
            <div className="rounded-2xl bg-auth-form-container p-6 shadow-sm border border-border/50">
              <h1 className="text-2xl font-semibold text-foreground md:text-3xl">
                {t('registerTitle')}
              </h1>

              <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4 text-left">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {success && (
                <Alert>
                  <AlertDescription>{success}</AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="firstName">{t('firstName')}</Label>
                  <Input id="firstName" {...register('firstName')} />
                  {errors.firstName && (
                    <p className="text-xs text-destructive">{errors.firstName.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="lastName">{t('lastName')}</Label>
                  <Input id="lastName" {...register('lastName')} />
                  {errors.lastName && (
                    <p className="text-xs text-destructive">{errors.lastName.message}</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">{t('email')}</Label>
                <Input id="email" type="email" autoComplete="email" {...register('email')} />
                {errors.email && (
                  <p className="text-xs text-destructive">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t('password') || 'Contraseña'}</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    {...register('password')}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <PasswordChecklist password={watch('password')} />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirmar contraseña</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
                )}
              </div>

              <div className="pt-2">
                <Button type="submit" className="w-full gap-2" disabled={isLoading}>
                  {isLoading ? (
                    t('loading')
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      {t('registerAction')}
                    </>
                  )}
                </Button>
              </div>
            </form>

            <div className="mt-6">
              <div className="relative flex items-center mb-6">
                <hr className="flex-grow border-border" />
                <span className="mx-3 shrink-0 text-xs text-muted-foreground bg-card px-2 rounded-sm">O continuar con</span>
                <hr className="flex-grow border-border" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Button
                  type="button"
                  className="w-full gap-2 bg-white text-slate-800 border border-slate-200 hover:bg-[#DCBE87] hover:border-[#DCBE87] transition-colors"
                  onClick={handleGoogleSignIn}
                  disabled={isGoogleLoading}
                  aria-label="Continuar con Google"
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
                  {isGoogleLoading ? t('loading') || 'Cargando...' : 'Google'}
                </Button>

                <Button asChild className="w-full gap-2 bg-[#6D5A45] text-white border-none hover:bg-[#584836] transition-colors">
                  <Link to={HOME_PATH}>
                    <User className="h-4 w-4" />
                    Invitado
                  </Link>
                </Button>
              </div>

              <p className="mt-4 text-sm text-muted-foreground">
                {t('registerHaveAccount')}{' '}
                <Link to="/login" className="text-primary underline">
                  {t('login')}
                </Link>
              </p>
            </div>
            </div>
          </div>
        </div>

        <div className="hidden lg:block">
          <div className="h-[calc(100vh-4rem)] w-full overflow-hidden rounded-3xl">
            <img
              src={bosqueLanding}
              alt=""
              aria-hidden="true"
              className="h-full w-full object-cover"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
