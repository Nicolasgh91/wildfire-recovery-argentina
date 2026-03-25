import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { User } from 'lucide-react'

import { AnimatedGradientText } from '@/components/ui/AnimatedGradientText'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useI18n } from '@/context/LanguageContext'
import bosqueLanding from '@/assets/bosque_landing.webp'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'

import { AuthFormOTP } from '@/components/auth/AuthFormOTP'
import { AuthFormEmail } from '@/components/auth/AuthFormEmail'
import { AuthFormOAuth } from '@/components/auth/AuthFormOAuth'

export default function LoginPage() {
  const location = useLocation()
  const { t } = useI18n()
  const idleToastShown = useRef(false)

  useEffect(() => {
    const reason = (location.state as { reason?: string } | undefined)?.reason
    if (reason === 'idle' && !idleToastShown.current) {
      idleToastShown.current = true
      toast.info(t('loginIdleSession'))
    }
  }, [location.state, t])

  useEffect(() => {
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia('(min-width: 1024px)')
    if (!mediaQuery.matches) return

    const link = document.createElement('link')
    link.rel = 'preload'
    link.as = 'image'
    link.href = bosqueLanding
    link.media = '(min-width: 1024px)'
    document.head.appendChild(link)

    return () => {
      document.head.removeChild(link)
    }
  }, [])

  return (
    <div className="relative min-h-screen bg-auth-page p-6 md:p-8">
      <Link to={LOGIN_PATH} className="absolute left-6 top-6 md:left-8 md:top-8" aria-label="Huella del fuego — Inicio">
        <BrandLogo size="md" showName={false} />
      </Link>

      <div className="grid min-h-[calc(100vh-3rem)] grid-cols-1 items-center gap-10 lg:grid-cols-2">
        <div className="flex items-center justify-center">
          <div className="w-full max-w-lg text-left pt-20 lg:pt-0">
            <section className="flex flex-col gap-4 mb-8">
              <AnimatedGradientText
                as="h1"
                text={t('loginHeroTitle')}
                className="text-4xl lg:text-5xl font-bold tracking-tight leading-tight"
                duration={1.2}
                delay={0.2}
                data-testid="hero-title"
              />
              <h2 className="text-xl lg:text-2xl text-muted-foreground font-medium">
                {t('loginHeroSubtitle')}
              </h2>
            </section>

            <div className="rounded-2xl bg-white/80 dark:bg-black/40 backdrop-blur-xl p-6 shadow-2xl border border-white/50 dark:border-white/10">
              <Tabs defaultValue="magic-link" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6 p-1 bg-slate-200/50 dark:bg-black/50 rounded-lg">
                    <TabsTrigger
                    value="magic-link"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 dark:data-[state=active]:bg-[#1E1E1E] dark:data-[state=active]:text-white text-slate-700 dark:text-slate-300 hover:text-foreground rounded-md transition-all duration-200 ease-in-out"
                  >
                    Enlace de acceso único
                  </TabsTrigger>
                  <TabsTrigger
                    value="password"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 dark:data-[state=active]:bg-[#1E1E1E] dark:data-[state=active]:text-white text-slate-700 dark:text-slate-300 hover:text-foreground rounded-md transition-all duration-200 ease-in-out"
                  >
                    Contraseña
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="magic-link" className="space-y-4">
                  <AuthFormOTP />
                </TabsContent>

                <TabsContent value="password" className="space-y-4">
                  <AuthFormEmail />
                </TabsContent>
              </Tabs>

              <div className="mt-6">
                <div className="relative flex items-center mb-6">
                  <div className="flex-grow border-t border-border" />
                  <span className="mx-3 shrink-0 text-xs text-slate-700 dark:text-slate-300 px-2">O continuar con</span>
                  <div className="flex-grow border-t border-border" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <AuthFormOAuth />

                  <Button asChild variant="outline" className="w-full gap-2 bg-white dark:bg-transparent border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white transition-all duration-200 ease-in-out hover:border-primary hover:bg-slate-100 hover:shadow-md hover:text-primary dark:hover:border-primary dark:hover:bg-slate-800 dark:hover:shadow-md dark:hover:text-primary">
                    <Link to={HOME_PATH}>
                      <User className="h-4 w-4" />
                      Invitado
                    </Link>
                  </Button>
                </div>

                <p className="mt-6 text-sm text-slate-700 dark:text-slate-300 text-center">
                  {t('noAccount')}{' '}
                  <Link to="/register" className="font-bold text-primary underline underline-offset-4 hover:underline dark:brightness-125">
                    {t('register')}
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
              decoding="async"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
