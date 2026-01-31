'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Trees, Map, ClipboardCheck, User, LogIn, LogOut, Globe, Sun, Moon, Flame } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useI18n } from '@/contexts/i18n-context'
import { useAuth } from '@/contexts/auth-context'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'

export function Navbar() {
  const pathname = usePathname()
  const { language, setLanguage, t } = useI18n()
  const { user, logout, isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()

  const navItems = [
    { href: '/', label: t('home'), icon: Trees },
    { href: '/fires', label: 'Incendios', icon: Flame },
    { href: '/map', label: t('map'), icon: Map },
    { href: '/audit', label: t('audit'), icon: ClipboardCheck },
  ]

  return (
    <>
      {/* Desktop Navigation */}
      <header className="hidden md:flex fixed top-0 left-0 right-0 z-50 h-16 items-center justify-between border-b border-border bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Link href="/" className="flex items-center gap-2">
          <Trees className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold text-foreground">ForestGuard</span>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                pathname === item.href
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
          <Link
            href="/certificates"
            className={cn(
              'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              pathname === '/certificates'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            {t('certificates')}
          </Link>
          <Link
            href="/shelters"
            className={cn(
              'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              pathname === '/shelters'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            {t('shelters')}
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <Globe className="h-5 w-5" />
                <span className="sr-only">Toggle language</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setLanguage('es')}>
                <span className={language === 'es' ? 'font-bold' : ''}>Español</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLanguage('en')}>
                <span className={language === 'en' ? 'font-bold' : ''}>English</span>
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
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link href="/login">
              <Button variant="default" size="sm" className="gap-2">
                <LogIn className="h-4 w-4" />
                {t('login')}
              </Button>
            </Link>
          )}
        </div>
      </header>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex flex-col items-center gap-1 px-3 py-2',
              pathname === item.href ? 'text-primary' : 'text-muted-foreground'
            )}
          >
            <item.icon className="h-5 w-5" />
            <span className="text-xs">{item.label}</span>
          </Link>
        ))}
        <Link
          href={isAuthenticated ? '/certificates' : '/login'}
          className={cn(
            'flex flex-col items-center gap-1 px-3 py-2',
            pathname === '/login' || pathname === '/certificates' ? 'text-primary' : 'text-muted-foreground'
          )}
        >
          <User className="h-5 w-5" />
          <span className="text-xs">{isAuthenticated ? t('profile') : t('login')}</span>
        </Link>
      </nav>
    </>
  )
}
