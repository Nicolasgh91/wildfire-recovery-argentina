import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Trees, AlertCircle, Mail } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { AnimatedGradientText } from '@/components/ui/AnimatedGradientText'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import bosqueLanding from '@/assets/bosque_landing.jpeg'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useI18n()
  const { signIn, signInWithGoogle } = useAuth()
  const idleToastShown = useRef(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  const from = (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname || '/'

  useEffect(() => {
    const reason = (location.state as { reason?: string } | undefined)?.reason
    if (reason === 'idle' && !idleToastShown.current) {
      idleToastShown.current = true
      toast.info('Sesión cerrada por inactividad')
    }
  }, [location.state])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError(t('loginError'))
      return
    }

    setIsLoading(true)

    try {
      await signIn(email, password)
      navigate(from, { replace: true })
    } catch {
      setError(t('loginInvalid'))
    }

    setIsLoading(false)
  }

  const handleGoogleSignIn = async () => {
    setError('')
    setIsGoogleLoading(true)

    try {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('auth:returnTo', from)
      }
      await signInWithGoogle()
    } catch {
      setError(t('loginInvalid'))
    }

    setIsGoogleLoading(false)
  }

  return (
    <div className="relative min-h-screen bg-background p-6 md:p-8">
      <Link to="/" className="absolute left-6 top-6 flex items-center gap-2 md:left-8 md:top-8">
        <Trees className="h-8 w-8 text-primary" />
        <span className="text-xl font-bold text-foreground">ForestGuard</span>
      </Link>

      <div className="grid min-h-[calc(100vh-3rem)] grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <div className="flex items-center justify-center">
          <div className="w-full max-w-lg text-left">
            {/* Hero Section */}
            <section className="flex flex-col gap-4 mb-8">
              {/* H1 - componente animado */}
              <AnimatedGradientText
                as="h1"
                text="La huella del fuego, vista desde el espacio."
                className="text-4xl lg:text-5xl font-bold tracking-tight leading-tight"
                duration={1.2}
                delay={0.2}
                data-testid="hero-title"
              />

              {/* H2 */}
              <h2 className="text-xl lg:text-2xl text-muted-foreground font-medium">
                Genera líneas de tiempo satelitales de incendios en Argentina.
              </h2>

              {/* Leyenda */}
              <p className="text-base text-muted-foreground/80 leading-relaxed">
                Compara el antes y el después: detecta revegetación natural o
                construcciones no autorizadas en zonas afectadas.
              </p>
            </section>

            <form onSubmit={handleSubmit} className="space-y-4 text-left" data-testid="login-form">
              {error && (
                <Alert variant="destructive" data-testid="login-error" role="alert" aria-live="polite">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">{t('email')}</Label>
                <Input
                  id="email"
                  data-testid="login-email"
                  type="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t('password')}</Label>
                <Input
                  id="password"
                  data-testid="login-password"
                  type="password"
                  placeholder="********"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>

              <div className="space-y-3 pt-2">
                <Button
                  type="button"
                  className="w-full gap-2"
                  onClick={handleGoogleSignIn}
                  disabled={isGoogleLoading}
                  aria-label={t('loginGoogle')}
                  data-testid="login-google"
                >
                  <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24">
                    <path
                      fill="#FFFFFF"
                      d="M23.22 12.27c0-.85-.08-1.48-.21-2.14H12v4.05h6.42c-.13 1.05-.84 2.63-2.42 3.69l-.02.14 3.49 2.71.24.02c2.19-2.02 3.51-4.99 3.51-8.47Z"
                    />
                    <path
                      fill="#FFFFFF"
                      d="M12 23c3.24 0 5.95-1.07 7.94-2.91l-3.78-2.93c-1.01.7-2.36 1.19-4.16 1.19-3.18 0-5.88-2.02-6.84-4.82l-.14.01-3.63 2.81-.05.13C3.32 20.68 7.32 23 12 23Z"
                    />
                    <path
                      fill="#FFFFFF"
                      d="M5.16 13.53A6.99 6.99 0 0 1 4.77 12c0-.53.09-1.04.23-1.53l-.01-.1-3.68-2.85-.12.06A11.97 11.97 0 0 0 0 12c0 1.94.47 3.78 1.3 5.41l3.86-2.88Z"
                    />
                    <path
                      fill="#FFFFFF"
                      d="M12 4.62c2.31 0 3.87 1 4.75 1.84l3.46-3.38C17.95.94 15.24 0 12 0 7.32 0 3.32 2.31 1.19 6.59l3.8 2.88C6.13 6.64 8.82 4.62 12 4.62Z"
                    />
                  </svg>
                  {isGoogleLoading ? 'Loading...' : t('loginGoogle')}
                </Button>

                <Button
                  type="submit"
                  data-testid="login-submit"
                  variant="outline"
                  className="w-full gap-2"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    'Loading...'
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      {t('loginEmail')}
                    </>
                  )}
                </Button>
              </div>
            </form>

            <div className="mt-6">
              <div className="relative flex items-center">
                <Separator className="absolute inset-0 top-1/2" />
                <span className="relative mx-auto bg-background px-3 text-xs text-muted-foreground">
                  {t('loginGuestDivider')}
                </span>
              </div>
              <Button asChild variant="secondary" className="mt-4 w-full" data-testid="login-guest">
                <Link to="/">{t('loginGuestAction')}</Link>
              </Button>
              <p className="mt-4 text-sm text-muted-foreground">
                {t('noAccount')}{' '}
                <Link to="/register" className="text-primary underline">
                  {t('register')}
                </Link>
              </p>
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
              decoding="async"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
