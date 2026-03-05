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

  return (
    <div className="relative min-h-screen bg-auth-page p-6 md:p-8">
      <Link to={LOGIN_PATH} className="absolute left-6 top-6 md:left-8 md:top-8">
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

            <div className="rounded-2xl bg-auth-form-container p-6 shadow-sm border border-border/50">
              <Tabs defaultValue="magic-link" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6 p-1 bg-black/5 dark:bg-muted/50 rounded-lg">
                  <TabsTrigger
                    value="magic-link"
                    className="data-[state=active]:bg-card data-[state=active]:shadow-sm data-[state=active]:text-foreground text-muted-foreground shadow-none transition-all duration-200 ease-in-out"
                  >
                    Enlace de acceso único
                  </TabsTrigger>
                  <TabsTrigger
                    value="password"
                    className="data-[state=active]:bg-card data-[state=active]:shadow-sm data-[state=active]:text-foreground text-muted-foreground shadow-none transition-all duration-200 ease-in-out"
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
                  <hr className="flex-grow border-border" />
                  <span className="mx-3 shrink-0 text-xs text-muted-foreground bg-card px-2 rounded-sm">O continuar con</span>
                  <hr className="flex-grow border-border" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <AuthFormOAuth />

                  <Button asChild className="w-full gap-2 bg-[#6D5A45] text-white border-none hover:bg-[#584836] transition-colors">
                    <Link to={HOME_PATH}>
                      <User className="h-4 w-4" />
                      Invitado
                    </Link>
                  </Button>
                </div>

                <p className="mt-6 text-sm text-muted-foreground text-center">
                  {t('noAccount')}{' '}
                  <Link to="/register" className="font-medium text-primary underline underline-offset-4">
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
