import { Link, NavLink } from 'react-router-dom'
import {
  Trees,
  User,
  LogIn,
  LogOut,
  Globe,
  Sun,
  Moon,
  Settings,
} from 'lucide-react'
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
import { isFeatureEnabled } from '@/lib/featureFlags'
import { BRAND } from '@/config/brand'
import { HOME_PATH } from '@/lib/routing'
import { PRIMARY_NAVIGATION_ITEMS, navLinkShouldUseExactMatch } from '@/features/navigation/config/navigation'

export function Navbar() {
  const { language, setLanguage, t } = useI18n()
  const { user, signOut, isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()

  return (
    <>
      {/* Desktop Navigation */}
      <header className="hidden md:flex fixed top-0 left-0 right-0 z-50 h-24 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Link to={HOME_PATH} className="flex items-center gap-2">
          <Trees className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold text-foreground">{BRAND.name}</span>
        </Link>

        <nav className="flex items-center gap-1">
          {PRIMARY_NAVIGATION_ITEMS.map((item) => (
            <NavLink
              key={item.to}
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
          ))}
          {isFeatureEnabled('certificates') && (
            <NavLink
              to="/certificates"
              end
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              {t('certificates')}
            </NavLink>
          )}
          {isFeatureEnabled('refuges') && (
            <NavLink
              to="/shelters"
              end
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              {t('shelters')}
            </NavLink>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {/* Language Toggle */}
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

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Auth */}
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

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex h-24 items-center justify-around border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        {PRIMARY_NAVIGATION_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={navLinkShouldUseExactMatch(item.activeMatch)}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-1 px-3 py-2',
                isActive ? 'text-primary' : 'text-muted-foreground',
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span className="text-xs">{t(item.labelKey)}</span>
          </NavLink>
        ))}
        <NavLink
          to={isAuthenticated ? '/profile' : '/login'}
          end
          className={({ isActive }) =>
            cn(
              'flex flex-col items-center gap-1 px-3 py-2',
              isActive ? 'text-primary' : 'text-muted-foreground',
            )
          }
        >
          <User className="h-5 w-5" />
          <span className="text-xs">{isAuthenticated ? t('profile') : t('login')}</span>
        </NavLink>
      </nav>
    </>
  )
}
