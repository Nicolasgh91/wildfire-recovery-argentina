import * as React from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { BRAND } from '@/config/brand'
import { BrandLogo } from '@/components/brand/BrandLogo'
import {
  type ExternalNavigationItem,
  getExternalItems,
  getInternalItems,
  getVisibleItemsByIds,
} from '@/features/navigation/config/navigation'
import { ExternalConfirmDialog } from '@/features/navigation/components/external-confirm-dialog'
import {
  DESKTOP_INFO_ITEM_IDS,
  DESKTOP_PRODUCT_ITEM_IDS,
  DESKTOP_SUPPORT_ITEM_IDS,
} from '@/features/navigation/config/access-groups'
import {
  type PublicSourceItem,
  type PublicSourceLink,
  PUBLIC_SOURCES_AR,
} from '@/features/navigation/config/public-sources'

const FOOTER_GROUPS: readonly {
  titleKey: 'footerProduct' | 'footerSupport' | 'footerInformative'
  itemIds: readonly string[]
}[] = [
  {
    titleKey: 'footerProduct',
    itemIds: DESKTOP_PRODUCT_ITEM_IDS,
  },
  {
    titleKey: 'footerSupport',
    itemIds: DESKTOP_SUPPORT_ITEM_IDS,
  },
  {
    titleKey: 'footerInformative',
    itemIds: DESKTOP_INFO_ITEM_IDS,
  },
] as const

interface FooterSectionProps {
  titleKey: 'footerProduct' | 'footerSupport' | 'footerInformative'
  itemIds: readonly string[]
  isAuthenticated: boolean
  onExternalClick: (item: ExternalNavigationItem) => void
}

function FooterSection({ titleKey, itemIds, isAuthenticated, onExternalClick }: FooterSectionProps) {
  const { t } = useI18n()
  const sectionItems = getVisibleItemsByIds(itemIds, isAuthenticated)
  const internalItems = getInternalItems(sectionItems)
  const externalItems = getExternalItems(sectionItems)

  if (internalItems.length === 0 && externalItems.length === 0) {
    return null
  }

  return (
    <div>
      <h3 className="mb-4 text-sm font-semibold tracking-wider text-foreground uppercase">
        {t(titleKey)}
      </h3>
      <ul className="flex flex-col gap-3">
        {internalItems.map((item) => (
          <li key={item.id}>
            <Link
              to={item.to}
              onClick={() => window.scrollTo(0, 0)}
              className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary"
            >
              <item.icon className="h-4 w-4" />
              {t(item.labelKey)}
            </Link>
          </li>
        ))}
        {externalItems.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onExternalClick(item)}
              className="flex items-center gap-2 text-left text-sm text-muted-foreground transition-colors hover:text-primary"
            >
              <item.icon className="h-4 w-4" />
              {t(item.labelKey)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface PublicSourcesProps {
  onExternalClick: (href: string, siteName: string) => void
}

function isPublicSourceGroup(item: PublicSourceItem): item is readonly PublicSourceLink[] {
  return Array.isArray(item)
}

function PublicSourcesColumn({ onExternalClick }: PublicSourcesProps) {
  const { t } = useI18n()

  return (
    <div>
      <h3 className="mb-4 text-sm font-semibold tracking-wider text-foreground uppercase">
        {t('footerPublicSources')}
      </h3>
      <TooltipProvider>
        <ul className="flex flex-col gap-3">
          {PUBLIC_SOURCES_AR.map((item, index) => {
            if (isPublicSourceGroup(item)) {
              return (
                <li
                  key={`group-${index}`}
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                >
                  <ExternalLink className="h-3 w-3 shrink-0" />
                  <div className="flex items-center gap-2">
                    {item.map((link, subIndex) => (
                      <React.Fragment key={link.href}>
                        <Tooltip delayDuration={300}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              onClick={() => onExternalClick(link.href, t(link.labelKey))}
                              className="truncate text-left transition-colors hover:text-primary"
                            >
                              {t(link.labelKey)}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{t(link.tooltipKey)}</p>
                          </TooltipContent>
                        </Tooltip>
                        {subIndex < item.length - 1 && <span>|</span>}
                      </React.Fragment>
                    ))}
                  </div>
                </li>
              )
            }

            return (
              <li key={item.href}>
                <Tooltip delayDuration={300}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => onExternalClick(item.href, t(item.labelKey))}
                      className="flex items-center gap-2 text-left text-sm text-muted-foreground transition-colors hover:text-primary"
                    >
                      <ExternalLink className="h-3 w-3 shrink-0" />
                      <span className="truncate">{t(item.labelKey)}</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t(item.tooltipKey)}</p>
                  </TooltipContent>
                </Tooltip>
              </li>
            )
          })}
        </ul>
      </TooltipProvider>
    </div>
  )
}

export function Footer() {
  const { t } = useI18n()
  const { isAuthenticated } = useAuth()
  const [pendingExternal, setPendingExternal] = React.useState<{ href: string; siteName: string } | null>(
    null,
  )

  const handleNavigationItemExternalClick = (item: ExternalNavigationItem) => {
    if (item.requiresExitConfirm) {
      setPendingExternal({ href: item.href, siteName: t(item.labelKey) })
      return
    }
    window.open(item.href, '_blank', 'noopener,noreferrer')
  }

  const handleRawExternalClick = (href: string, siteName: string) => {
    setPendingExternal({ href, siteName })
  }

  return (
    <>
      <footer className="hidden border-t border-border bg-card md:block">
        <div className="container mx-auto px-6 py-12">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-5">
            <div className="flex flex-col gap-4">
              <div>
                <BrandLogo size="md" />
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {t('footerBrandLine1')} {t('footerBrandLine2')}
              </p>
            </div>

            {FOOTER_GROUPS.map((group) => (
              <FooterSection
                key={group.titleKey}
                titleKey={group.titleKey}
                itemIds={group.itemIds}
                isAuthenticated={isAuthenticated}
                onExternalClick={handleNavigationItemExternalClick}
              />
            ))}

            <PublicSourcesColumn onExternalClick={handleRawExternalClick} />
          </div>

          <div className="mt-12 border-t border-border pt-8">
            <div className="mb-8">
              <h3 className="mb-3 text-xs font-semibold tracking-wider text-foreground uppercase">
                {t('footerLegalTitle')}
              </h3>
              <p className="mb-2 text-xs leading-relaxed text-muted-foreground">
                {t('footerLegalP1')}
              </p>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {t('footerLegalP2')}
              </p>
            </div>
            <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
              <p className="text-sm text-muted-foreground">
                &copy; {new Date().getFullYear()} {BRAND.name} Argentina. {t('footerCopyright')}
              </p>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <span>{t('footerMadeWith')}</span>
                <span className="text-destructive" aria-label="corazon">
                  {'\u2764\uFE0F'}
                </span>
                <span>{t('footerProtectForests')}</span>
              </div>
            </div>
          </div>
        </div>
      </footer>

      <ExternalConfirmDialog
        open={pendingExternal !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setPendingExternal(null)
        }}
        href={pendingExternal?.href ?? ''}
        siteName={pendingExternal?.siteName ?? ''}
      />
    </>
  )
}
