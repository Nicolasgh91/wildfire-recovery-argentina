import { ChevronRight, ExternalLink } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { useI18n } from '@/context/LanguageContext'
import { cn } from '@/lib/utils'
import {
  getVisibleItemsByIds,
  getExternalItems,
  getInternalItems,
  navLinkShouldUseExactMatch,
} from '@/features/navigation/config/navigation'
import {
  MOBILE_MORE_INFO_ITEM_IDS,
  MOBILE_SUPPORT_ITEM_IDS,
} from '@/features/navigation/config/access-groups'
import { PUBLIC_SOURCES_AR } from '@/features/navigation/config/public-sources'

interface ExternalNavigationIntent {
  href: string
  siteName: string
}

interface NavigationDrawerCollapsibleGroupsProps {
  isAuthenticated: boolean
  onInternalNavigate: (path: string) => void
  onExternalNavigate: (intent: ExternalNavigationIntent) => void
}

export function NavigationDrawerCollapsibleGroups({
  isAuthenticated,
  onInternalNavigate,
  onExternalNavigate,
}: NavigationDrawerCollapsibleGroupsProps) {
  const { t } = useI18n()

  const supportItems = getVisibleItemsByIds(MOBILE_SUPPORT_ITEM_IDS, isAuthenticated)
  const supportInternalItems = getInternalItems(supportItems)
  const supportExternalItems = getExternalItems(supportItems)

  const infoItems = getVisibleItemsByIds(MOBILE_MORE_INFO_ITEM_IDS, isAuthenticated)
  const infoInternalItems = getInternalItems(infoItems)
  const infoExternalItems = getExternalItems(infoItems)

  const publicSourceLinks = PUBLIC_SOURCES_AR.flatMap((entry) => (Array.isArray(entry) ? entry : [entry]))

  return (
    <Accordion type="multiple" className="w-full" data-testid="drawer-collapsible-groups">
      <AccordionItem value="support">
        <AccordionTrigger className="px-1 text-xs font-semibold tracking-wide text-mobile-nav-section-heading uppercase">
          {t('footerSupport')}
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1">
            {supportInternalItems.map((item) => (
              <NavLink
                key={`support-${item.id}`}
                to={item.to}
                end={navLinkShouldUseExactMatch(item.activeMatch)}
                onClick={() => onInternalNavigate(item.to)}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-[44px] items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-mobile-nav-primary text-mobile-nav-primary-foreground'
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
            ))}
            {supportExternalItems.map((item) => (
              <button
                key={`support-${item.id}`}
                type="button"
                onClick={() => onExternalNavigate({ href: item.href, siteName: t(item.labelKey) })}
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
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="more-information">
        <AccordionTrigger className="px-1 text-xs font-semibold tracking-wide text-mobile-nav-section-heading uppercase">
          {t('navMoreInformation')}
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1">
            {infoInternalItems.map((item) => (
              <NavLink
                key={`info-${item.id}`}
                to={item.to}
                end={navLinkShouldUseExactMatch(item.activeMatch)}
                onClick={() => onInternalNavigate(item.to)}
                className={({ isActive }) =>
                  cn(
                    'flex min-h-[44px] items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-mobile-nav-primary text-mobile-nav-primary-foreground'
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
            ))}
            {infoExternalItems.map((item) => (
              <button
                key={`info-${item.id}`}
                type="button"
                onClick={() => onExternalNavigate({ href: item.href, siteName: t(item.labelKey) })}
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
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="public-sources">
        <AccordionTrigger className="px-1 text-xs font-semibold tracking-wide text-mobile-nav-section-heading uppercase">
          {t('footerPublicSources')}
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-1">
            {publicSourceLinks.map((link) => (
              <button
                key={`public-${link.href}`}
                type="button"
                onClick={() => onExternalNavigate({ href: link.href, siteName: t(link.labelKey) })}
                className="flex min-h-[44px] w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm text-mobile-nav-foreground transition-colors hover:bg-mobile-nav-muted"
              >
                <span className="flex items-center gap-2">
                  <ExternalLink className="h-4 w-4" />
                  {t(link.labelKey)}
                </span>
                <ExternalLink className="h-4 w-4 opacity-70" />
              </button>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
