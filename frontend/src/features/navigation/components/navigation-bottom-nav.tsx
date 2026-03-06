import { Home, Map, Menu, Search } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useI18n } from '@/context/LanguageContext'
import { HOME_PATH } from '@/lib/routing'
import { Z_INDEX } from '@/features/navigation/config/z-index'

interface NavigationBottomNavProps {
  onMenuPress: () => void
}

export function NavigationBottomNav({ onMenuPress }: NavigationBottomNavProps) {
  const { t } = useI18n()

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-mobile-nav-border bg-mobile-nav/95 backdrop-blur supports-[backdrop-filter]:bg-mobile-nav/60 md:hidden"
      style={{ zIndex: Z_INDEX.NAVBAR }}
      aria-label={t('navMenu')}
    >
      <div className="grid grid-cols-4 gap-1 px-2 pb-[env(safe-area-inset-bottom)] pt-1">
        <NavLink
          to={HOME_PATH}
          end
          aria-label={t('home')}
          className={({ isActive }) =>
            cn(
              'flex h-11 min-h-[44px] flex-col items-center justify-center rounded-md text-xs font-medium',
              isActive ? 'text-mobile-nav-primary' : 'text-mobile-nav-foreground',
            )
          }
        >
          <Home className="h-5 w-5" />
          <span>{t('home')}</span>
        </NavLink>
        <NavLink
          to="/map"
          end
          aria-label={t('map')}
          className={({ isActive }) =>
            cn(
              'flex h-11 min-h-[44px] flex-col items-center justify-center rounded-md text-xs font-medium',
              isActive ? 'text-mobile-nav-primary' : 'text-mobile-nav-foreground',
            )
          }
        >
          <Map className="h-5 w-5" />
          <span>{t('map')}</span>
        </NavLink>
        <NavLink
          to="/exploracion"
          end
          aria-label={t('reports')}
          className={({ isActive }) =>
            cn(
              'flex h-11 min-h-[44px] flex-col items-center justify-center rounded-md text-xs font-medium',
              isActive ? 'text-mobile-nav-primary' : 'text-mobile-nav-foreground',
            )
          }
        >
          <Search className="h-5 w-5" />
          <span>{t('reports')}</span>
        </NavLink>
        <button
          type="button"
          onClick={onMenuPress}
          aria-label={t('navMenu')}
          className="flex h-11 min-h-[44px] flex-col items-center justify-center rounded-md text-xs font-medium text-mobile-nav-foreground"
        >
          <Menu className="h-5 w-5" />
          <span>{t('navMenu')}</span>
        </button>
      </div>
    </nav>
  )
}

