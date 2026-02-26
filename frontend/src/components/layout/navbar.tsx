import { useMemo, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Globe, Lock, LogIn, LogOut, Moon, Settings, Sun, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'
import {
  getInternalItems,
  getVisibleItems,
  isLockedPreview,
  navLinkShouldUseExactMatch,
} from '@/features/navigation/config/navigation'
import { NavigationBottomNav } from '@/features/navigation/components/navigation-bottom-nav'
import { NavigationTopbarTablet } from '@/features/navigation/components/navigation-topbar-tablet'
import { NavigationDrawer } from '@/features/navigation/components/navigation-drawer'
import { RestrictedAccessDialog } from '@/components/auth/RestrictedAccessDialog'

function DesktopNavbar() {
  const { language, setLanguage, t } = useI18n()
  const { user, signOut, isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [lockedTargetPath, setLockedTargetPath] = useState<string | null>(null)

  const desktopItems = useMemo(
    () => [
      ...getInternalItems(
        getVisibleItems('explore', isAuthenticated, { includeLockedPreviews: true }),
      ),
      ...getInternalItems(
        getVisibleItems('tools', isAuthenticated, { includeLockedPreviews: true }),
      ),
    ],
    [isAuthenticated],
  )

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 hidden h-24 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60 lg:flex">
        <Link to={HOME_PATH}>
          <BrandLogo size="md" />
        </Link>

        <nav className="flex items-center gap-1">
          {desktopItems.map((item) => {
            const locked = isLockedPreview(item, isAuthenticated)
            if (locked) {
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setLockedTargetPath(item.to)}
                  aria-label={`${t(item.labelKey)} - requiere inicio de sesion`}
                  className={cn(
                    'flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {t(item.labelKey)}
                  <Lock className="h-3.5 w-3.5 opacity-80" />
                </button>
              )
            }

            return (
              <NavLink
                key={item.id}
                to={item.to}
                end={navLinkShouldUseExactMatch(item.activeMatch)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {t(item.labelKey)}
              </NavLink>
            )
          })}
        </nav>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <Globe className="h-5 w-5" />
                <span className="sr-only">{t('toggleLanguage')}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setLanguage('es')}>
                <span className={language === 'es' ? 'font-bold' : ''}>{t('languageSpanish')}</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLanguage('en')}>
                <span className={language === 'en' ? 'font-bold' : ''}>{t('languageEnglish')}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <User className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled>
                  <span className="text-xs text-muted-foreground">{user?.email}</span>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/profile" className="flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    {t('editProfile')}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={signOut}>
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild variant="default" size="sm" className="gap-2">
              <Link to="/login">
                <LogIn className="h-4 w-4" />
                {t('login')}
              </Link>
            </Button>
          )}
        </div>
      </header>

      <NavigationBottomNav onMenuPress={() => setDrawerOpen(true)} />
      <NavigationTopbarTablet onMenuPress={() => setDrawerOpen(true)} />
      <NavigationDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onLockedItemIntent={(path) => setLockedTargetPath(path)}
      />
      <RestrictedAccessDialog
        open={lockedTargetPath !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setLockedTargetPath(null)
        }}
        onGoBack={() => {
          setLockedTargetPath(null)
        }}
        onLogin={() => {
          if (!lockedTargetPath) return
          navigate(LOGIN_PATH, {
            state: { from: { pathname: lockedTargetPath }, reason: 'nav_locked_item' },
          })
          setLockedTargetPath(null)
        }}
      />
    </>
  )
}

export function Navbar() {
  return <DesktopNavbar />
}
