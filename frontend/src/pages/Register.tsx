import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Trees, AlertCircle, Mail } from 'lucide-react'
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
import bosqueLanding from '@/assets/bosque_landing.jpeg'

type RegisterValues = {
  firstName: string
  lastName: string
  email: string
}

export default function RegisterPage() {
  const { t } = useI18n()
  const { signUpWithEmail } = useAuth()

  const registerSchema = z.object({
    firstName: z.string().min(2, t('validationRequired')).max(50, t('validationMax50')),
    lastName: z.string().min(2, t('validationRequired')).max(50, t('validationMax50')),
    email: z.string().email(t('validationInvalidEmail')),
  })

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
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
        firstName: values.firstName,
        lastName: values.lastName,
      })
      setSuccess(t('registerSuccess'))
    } catch {
      setError(t('registerError'))
    }

    setIsLoading(false)
  }

  return (
    <div className="relative min-h-screen bg-background p-6 md:p-8">
      <Link to="/" className="absolute left-6 top-6 flex items-center gap-2 md:left-8 md:top-8">
        <Trees className="h-8 w-8 text-primary" />
        <span className="text-xl font-bold text-foreground">ForestGuard</span>
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
                <Link to="/">{t('registerGuestAction')}</Link>
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
              alt="Bosque ForestGuard"
              className="h-full w-full object-cover"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
