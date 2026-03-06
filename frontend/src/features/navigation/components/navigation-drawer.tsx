import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { Dialog, DialogHeader, DialogOverlay, DialogPortal, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { useTheme } from 'next-themes'
import {
  type ExternalNavigationItem,
} from '@/features/navigation/config/navigation'
import { NavigationMenuSections } from '@/features/navigation/components/navigation-menu-sections'
import { NavigationDrawerCollapsibleGroups } from '@/features/navigation/components/navigation-drawer-collapsible-groups'
import { ExternalConfirmDialog } from '@/features/navigation/components/external-confirm-dialog'
import { LogoutAction } from '@/features/account/components/logout-action'
import {
  criticalDialogContentClasses,
  criticalDialogDescriptionClasses,
  criticalDialogTitleClasses,
} from '@/components/ui/critical-dialog-styles'
import { Z_INDEX } from '@/features/navigation/config/z-index'
import { cn } from '@/lib/utils'

interface NavigationDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onLockedItemIntent: (path: string) => void
}

export function NavigationDrawer({ open, onOpenChange, onLockedItemIntent }: NavigationDrawerProps) {
  const { language, setLanguage, t } = useI18n()
  const { isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const [externalTarget, setExternalTarget] = useState<{ href: string; siteName: string } | null>(null)
  const [termsOpen, setTermsOpen] = useState(false)

  const closeDrawer = () => onOpenChange(false)

  const handleInternalNavigate = (path: string) => {
    navigate(path)
    closeDrawer()
  }

  const handleLockedNavigate = (path: string) => {
    onLockedItemIntent(path)
    closeDrawer()
  }

  const handleExternalClick = (item: ExternalNavigationItem) => {
    if (item.requiresExitConfirm) {
      setExternalTarget({ href: item.href, siteName: t(item.labelKey) })
      return
    }
    window.open(item.href, '_blank', 'noopener,noreferrer')
    closeDrawer()
  }

  const handleCollapsibleExternalNavigate = (intent: { href: string; siteName: string }) => {
    setExternalTarget(intent)
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="left" className="w-[320px] overflow-y-auto border-r-0 bg-mobile-nav sm:max-w-sm">
          <SheetHeader className="px-4 pb-2">
            <SheetTitle>
              <Link to="/home" className="inline-flex" onClick={closeDrawer}>
                <BrandLogo size="sm" />
              </Link>
            </SheetTitle>
            <SheetDescription>{t('navMenu')}</SheetDescription>
          </SheetHeader>

          <div className="space-y-6 px-4 pb-6">
            <NavigationMenuSections
              sections={['explore', 'tools']}
              isAuthenticated={isAuthenticated}
              onInternalNavigate={handleInternalNavigate}
              onLockedNavigate={handleLockedNavigate}
              onExternalClick={handleExternalClick}
              includeLockedPreviews
            />

            <NavigationDrawerCollapsibleGroups
              isAuthenticated={isAuthenticated}
              onInternalNavigate={handleInternalNavigate}
              onExternalNavigate={handleCollapsibleExternalNavigate}
            />

            <NavigationMenuSections
              sections={['account']}
              isAuthenticated={isAuthenticated}
              onInternalNavigate={handleInternalNavigate}
              onLockedNavigate={handleLockedNavigate}
              onExternalClick={handleExternalClick}
            />

            <section className="space-y-2">
              <h3 className="px-1 text-xs font-semibold tracking-wide text-mobile-nav-section-heading uppercase">
                {t('navPreferences')}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className={cn(
                    language === 'es'
                      ? 'border-mobile-nav-primary bg-mobile-nav-primary text-mobile-nav-primary-foreground hover:bg-mobile-nav-primary hover:text-mobile-nav-primary-foreground'
                      : 'border-mobile-nav-border bg-transparent text-mobile-nav-muted-foreground hover:bg-mobile-nav-muted',
                  )}
                  onClick={() => setLanguage('es')}
                >
                  ES
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={cn(
                    language === 'en'
                      ? 'border-mobile-nav-primary bg-mobile-nav-primary text-mobile-nav-primary-foreground hover:bg-mobile-nav-primary hover:text-mobile-nav-primary-foreground'
                      : 'border-mobile-nav-border bg-transparent text-mobile-nav-muted-foreground hover:bg-mobile-nav-muted',
                  )}
                  onClick={() => setLanguage('en')}
                >
                  EN
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="col-span-2 border-mobile-nav-border bg-transparent text-mobile-nav-foreground hover:bg-mobile-nav-muted"
                  onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                >
                  {theme === 'dark' ? <Sun className="mr-2 h-4 w-4" /> : <Moon className="mr-2 h-4 w-4" />}
                  {theme === 'dark' ? 'Light' : 'Dark'}
                </Button>
              </div>
            </section>

            {isAuthenticated && (
              <LogoutAction
                className="w-full"
                onAfterLogout={() => {
                  closeDrawer()
                }}
              />
            )}

            <section className="border-t border-mobile-nav-border pt-4">
              <button
                type="button"
                onClick={() => setTermsOpen(true)}
                className="text-xs text-mobile-nav-muted-foreground underline underline-offset-2 hover:text-mobile-nav-foreground"
              >
                Términos de uso
              </button>
            </section>
          </div>
        </SheetContent>
      </Sheet>

      <Dialog open={termsOpen} onOpenChange={setTermsOpen}>
        <DialogPortal>
          <DialogOverlay style={{ zIndex: Z_INDEX.MODAL_CRITICAL }} />
          <DialogPrimitive.Content
            style={{ zIndex: Z_INDEX.MODAL_CRITICAL }}
            className={cn(
              criticalDialogContentClasses,
              'fixed top-[50%] left-[50%] grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg p-6 sm:max-w-lg max-h-[80vh] overflow-y-auto data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 duration-200',
            )}
          >
            <DialogHeader>
              <DialogTitle className={criticalDialogTitleClasses}>Términos de uso</DialogTitle>
            </DialogHeader>
            <div className={cn('space-y-4 text-sm leading-relaxed', criticalDialogDescriptionClasses)}>
              <p>
                Aviso legal sobre el uso de datos: La información, análisis y reportes generados por esta plataforma tienen un fin estrictamente informativo, educativo y de investigación. Los datos provienen del procesamiento automatizado de fuentes públicas y no constituyen evidencia legal, pericial ni oficial de ningún tipo. Los análisis satelitales pueden contener márgenes de error y no reemplazan el criterio de las autoridades competentes.
              </p>
              <p>
                Fuentes de datos: Los focos de calor son provistos por el sistema FIRMS de la NASA. El procesamiento de imágenes satelitales se realiza a través de Google Earth Engine, utilizando datos públicos de las misiones Landsat (USGS) y Sentinel (ESA).
              </p>
            </div>
            <DialogPrimitive.Close className="text-critical-dialog-foreground absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-critical-dialog-foreground/20 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none">
              <span className="sr-only">Cerrar</span>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </DialogPrimitive.Close>
          </DialogPrimitive.Content>
        </DialogPortal>
      </Dialog>

      <ExternalConfirmDialog
        open={externalTarget !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setExternalTarget(null)
        }}
        href={externalTarget?.href ?? ''}
        siteName={externalTarget?.siteName ?? ''}
      />
    </>
  )
}
