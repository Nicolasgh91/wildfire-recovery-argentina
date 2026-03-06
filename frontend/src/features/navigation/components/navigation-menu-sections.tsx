import { NavLink } from 'react-router-dom'
import { ChevronRight, ExternalLink, Lock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useI18n } from '@/context/LanguageContext'
import {
  type ExternalNavigationItem,
  type InternalNavigationItem,
  type NavigationSection,
  getInternalItems,
  getVisibleItems,
  getExternalItems,
  isLockedPreview,
  navLinkShouldUseExactMatch,
} from '@/features/navigation/config/navigation'

const SECTION_LABELS: Record<NavigationSection, 'navExplore' | 'navTools' | 'navAccount' | 'navHelp'> = {
  explore: 'navExplore',
  tools: 'navTools',
  account: 'navAccount',
  help: 'navHelp',
}

interface NavigationMenuSectionsProps {
  sections: NavigationSection[]
  isAuthenticated: boolean
  onInternalNavigate: (path: string) => void
  onLockedNavigate: (path: string) => void
  onExternalClick: (item: ExternalNavigationItem) => void
  includeLockedPreviews?: boolean
}

export function NavigationMenuSections({
  sections,
  isAuthenticated,
  onInternalNavigate,
  onLockedNavigate,
  onExternalClick,
  includeLockedPreviews = false,
}: NavigationMenuSectionsProps) {
  const { t } = useI18n()

  return (
    <div className="space-y-6">
      {sections.map((section) => {
        const visible = getVisibleItems(section, isAuthenticated, { includeLockedPreviews })
        const internalItems = getInternalItems(visible)
        const externalItems = getExternalItems(visible)

        if (visible.length === 0) return null

        return (
          <section key={section} className="space-y-2">
            <h3 className="px-1 text-xs font-semibold tracking-wide text-mobile-nav-section-heading uppercase">
              {t(SECTION_LABELS[section])}
            </h3>
            <div className="space-y-1">
              {internalItems.map((item) => {
                if (isLockedPreview(item, isAuthenticated)) {
                  return (
                    <LockedMenuItem
                      key={item.id}
                      item={item}
                      onLockedNavigate={onLockedNavigate}
                    />
                  )
                }

                return (
                  <NavLink
                    key={item.id}
                    to={item.to}
                    end={navLinkShouldUseExactMatch(item.activeMatch)}
                    onClick={() => onInternalNavigate(item.to)}
                    className={({ isActive }) =>
                      cn(
                        'flex min-h-[44px] items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                        isActive
                          ? 'bg-mobile-nav-primary text-mobile-nav-primary-foreground'
                          : item.id === 'login'
                            ? 'border border-mobile-nav-primary text-mobile-nav-primary bg-transparent hover:bg-mobile-nav-muted'
                            : 'text-mobile-nav-foreground hover:bg-mobile-nav-muted',
                      )
                    }
                  >
                    <span className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      {t(item.labelKey)}
                    </span>
                    <ChevronRight className="h-4 w-4 opacity-60" />
                  </NavLink>
                )
              })}
              {externalItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onExternalClick(item)}
                  className="flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm text-mobile-nav-foreground transition-colors hover:bg-mobile-nav-muted"
                >
                  <span className="flex items-center gap-2">
                    <item.icon className="h-4 w-4" />
                    {t(item.labelKey)}
                  </span>
                  <ExternalLink className="h-4 w-4 opacity-70" />
                </button>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}

function LockedMenuItem({
  item,
  onLockedNavigate,
}: {
  item: InternalNavigationItem
  onLockedNavigate: (path: string) => void
}) {
  const { t } = useI18n()

  return (
    <button
      type="button"
      onClick={() => onLockedNavigate(item.to)}
      aria-label={`${t(item.labelKey)} - requiere inicio de sesion`}
      className="flex min-h-[44px] w-full items-center justify-between rounded-md border border-mobile-nav-border/60 bg-mobile-nav-muted/30 px-3 py-2 text-left text-sm text-mobile-nav-muted-foreground transition-colors hover:bg-mobile-nav-muted hover:text-mobile-nav-foreground"
    >
      <span className="flex items-center gap-2">
        <item.icon className="h-4 w-4" />
        {t(item.labelKey)}
      </span>
      <Lock className="h-3.5 w-3.5 opacity-80" />
    </button>
  )
}
