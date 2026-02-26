import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Mail, Eye, EyeOff, Check, X } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import bosqueLanding from '@/assets/bosque_landing.webp'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'

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
          <li key={idx} className={`flex items-center gap-2 ${met ? 'text-green-600 dark:text-green-500' : 'text-muted-foreground'}`}>
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
  const { signUpWithEmail } = useAuth()

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

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
  })

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

  return (
    <div className="relative min-h-screen bg-background p-6 md:p-8">
      <Link to={LOGIN_PATH} className="absolute left-6 top-6 md:left-8 md:top-8">
        <BrandLogo size="md" />
      </Link>

      <div className="grid min-h-[calc(100vh-3rem)] grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <div className="flex items-center justify-center">
          <div className="w-full max-w-[420px] text-center">
            <h1 className="text-2xl font-semibold text-foreground md:text-3xl">
              {t('registerTitle')}
            </h1>
            <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground md:text-base">
              {t('registerSubtitle')}
            </p>

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
              <div className="relative flex items-center">
                <Separator className="absolute inset-0 top-1/2" />
                <span className="relative mx-auto bg-background px-3 text-xs text-muted-foreground">
                  {t('registerGuestDivider')}
                </span>
              </div>
              <Button asChild variant="secondary" className="mt-4 w-full">
                <Link to={HOME_PATH}>{t('registerGuestAction')}</Link>
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

        <div className="hidden lg:block">
          <div className="h-[calc(100vh-4rem)] w-full overflow-hidden rounded-3xl">
            <img
              src={bosqueLanding}
              alt="Bosque"
              className="h-full w-full object-cover"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
