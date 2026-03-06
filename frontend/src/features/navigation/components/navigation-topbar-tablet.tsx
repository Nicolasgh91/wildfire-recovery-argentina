import { Menu } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { HOME_PATH } from '@/lib/routing'
import { Z_INDEX } from '@/features/navigation/config/z-index'

interface NavigationTopbarTabletProps {
  onMenuPress: () => void
}

export function NavigationTopbarTablet({ onMenuPress }: NavigationTopbarTabletProps) {
  const { t } = useI18n()

  return (
    <header
      className="fixed top-0 left-0 right-0 hidden h-24 items-center justify-between border-b border-mobile-nav-border bg-mobile-nav/95 px-6 text-mobile-nav-foreground backdrop-blur supports-[backdrop-filter]:bg-mobile-nav/60 md:flex lg:hidden"
      style={{ zIndex: Z_INDEX.NAVBAR }}
    >
      <Link to={HOME_PATH}>
        <BrandLogo size="md" nameClassName="text-mobile-nav-foreground" />
      </Link>
      <Button
        variant="ghost"
        size="icon"
        onClick={onMenuPress}
        aria-label={t('navOpenMenu')}
      >
        <Menu className="h-5 w-5" />
      </Button>
    </header>
  )
}

