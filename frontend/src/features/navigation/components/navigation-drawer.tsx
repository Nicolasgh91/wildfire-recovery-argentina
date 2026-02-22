import { Moon, Sun, Trees } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { BRAND } from '@/config/brand'
import { useTheme } from 'next-themes'
import {
  type ExternalNavigationItem,
} from '@/features/navigation/config/navigation'
import { NavigationMenuSections } from '@/features/navigation/components/navigation-menu-sections'
import { NavigationDrawerCollapsibleGroups } from '@/features/navigation/components/navigation-drawer-collapsible-groups'
import { ExternalConfirmDialog } from '@/features/navigation/components/external-confirm-dialog'
import { LogoutAction } from '@/features/account/components/logout-action'

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
        <SheetContent side="left" className="w-[320px] overflow-y-auto sm:max-w-sm">
          <SheetHeader className="px-4 pb-2">
            <SheetTitle>
              <Link to="/home" className="inline-flex items-center gap-2" onClick={closeDrawer}>
                <Trees className="h-6 w-6 text-primary" />
                <span>{BRAND.name}</span>
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
              <h3 className="px-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {t('navPreferences')}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant={language === 'es' ? 'default' : 'outline'}
                  onClick={() => setLanguage('es')}
                >
                  ES
                </Button>
                <Button
                  type="button"
                  variant={language === 'en' ? 'default' : 'outline'}
                  onClick={() => setLanguage('en')}
                >
                  EN
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="col-span-2"
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
          </div>
        </SheetContent>
      </Sheet>

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
