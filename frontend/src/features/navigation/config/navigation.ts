import {
  BookOpen,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Flame,
  GraduationCap,
  HelpCircle,
  LogIn,
  Mail,
  Map as MapIcon,
  Trees,
  User,
  type LucideIcon,
} from 'lucide-react'
import type { TranslationKey } from '@/data/translations'
import { isFeatureEnabled } from '@/lib/featureFlags'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'

export type NavigationActiveMatch = 'exact' | 'prefix'
export type NavigationSection = 'explore' | 'tools' | 'account' | 'help'
export type NavigationVisibility = 'always' | 'auth_only' | 'guest_only'
export type NavigationGuestPreview = 'hidden' | 'locked'

interface BaseNavigationItem {
  id: string
  section: NavigationSection
  labelKey: TranslationKey
  visibility: NavigationVisibility
  order: number
}

export interface InternalNavigationItem extends BaseNavigationItem {
  kind: 'internal'
  to: string
  icon: LucideIcon
  activeMatch: NavigationActiveMatch
  featureFlag?: string
  guestPreview?: NavigationGuestPreview
}

export interface ExternalNavigationItem extends BaseNavigationItem {
  kind: 'external'
  href: string
  icon: LucideIcon
  requiresExitConfirm: boolean
}

export type NavigationItem = InternalNavigationItem | ExternalNavigationItem

export const NAVIGATION_SECTIONS: readonly NavigationSection[] = [
  'explore',
  'tools',
  'account',
  'help',
] as const

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    kind: 'internal',
    id: 'home',
    section: 'explore',
    to: HOME_PATH,
    labelKey: 'home',
    icon: Trees,
    activeMatch: 'exact',
    visibility: 'always',
    order: 10,
  },
  {
    kind: 'internal',
    id: 'map',
    section: 'explore',
    to: '/map',
    labelKey: 'map',
    icon: MapIcon,
    activeMatch: 'exact',
    visibility: 'always',
    order: 20,
  },
  {
    kind: 'internal',
    id: 'exploration',
    section: 'explore',
    to: '/exploracion',
    labelKey: 'reports',
    icon: FileText,
    activeMatch: 'exact',
    visibility: 'always',
    order: 30,
  },
  {
    kind: 'internal',
    id: 'fires-history',
    section: 'tools',
    to: '/fires/history',
    labelKey: 'fireHistory',
    icon: Flame,
    activeMatch: 'prefix',
    visibility: 'auth_only',
    guestPreview: 'locked',
    order: 40,
  },
  {
    kind: 'internal',
    id: 'audit',
    section: 'tools',
    to: '/audit',
    labelKey: 'audit',
    icon: ClipboardCheck,
    activeMatch: 'exact',
    visibility: 'auth_only',
    guestPreview: 'locked',
    order: 50,
  },
  {
    kind: 'internal',
    id: 'certificates',
    section: 'tools',
    to: '/certificates',
    labelKey: 'certificates',
    icon: ClipboardCheck,
    activeMatch: 'exact',
    visibility: 'always',
    order: 55,
    featureFlag: 'certificates',
  },
  {
    kind: 'internal',
    id: 'shelters',
    section: 'tools',
    to: '/shelters',
    labelKey: 'shelters',
    icon: MapIcon,
    activeMatch: 'exact',
    visibility: 'always',
    order: 56,
    featureFlag: 'refuges',
  },
  {
    kind: 'internal',
    id: 'profile',
    section: 'account',
    to: '/profile',
    labelKey: 'profile',
    icon: User,
    activeMatch: 'exact',
    visibility: 'auth_only',
    order: 60,
  },
  {
    kind: 'internal',
    id: 'login',
    section: 'account',
    to: LOGIN_PATH,
    labelKey: 'login',
    icon: LogIn,
    activeMatch: 'exact',
    visibility: 'guest_only',
    order: 70,
  },
  {
    kind: 'internal',
    id: 'faq',
    section: 'help',
    to: '/faq',
    labelKey: 'footerLinkFaq',
    icon: HelpCircle,
    activeMatch: 'exact',
    visibility: 'always',
    order: 80,
  },
  {
    kind: 'internal',
    id: 'manual',
    section: 'help',
    to: '/manual',
    labelKey: 'footerLinkManual',
    icon: BookOpen,
    activeMatch: 'exact',
    visibility: 'always',
    order: 90,
  },
  {
    kind: 'internal',
    id: 'glossary',
    section: 'help',
    to: '/glossary',
    labelKey: 'footerLinkGlossary',
    icon: GraduationCap,
    activeMatch: 'exact',
    visibility: 'always',
    order: 100,
  },
  {
    kind: 'internal',
    id: 'contact',
    section: 'help',
    to: '/contact',
    labelKey: 'footerLinkContact',
    icon: Mail,
    activeMatch: 'exact',
    visibility: 'always',
    order: 110,
  },
  {
    kind: 'external',
    id: 'api-docs',
    section: 'help',
    href: 'https://forestguard.freedynamicdns.org/docs',
    labelKey: 'footerLinkApiDocs',
    icon: ExternalLink,
    requiresExitConfirm: true,
    visibility: 'always',
    order: 120,
  },
  {
    kind: 'external',
    id: 'protected-areas',
    section: 'help',
    href: 'https://www.argentina.gob.ar/parquesnacionales',
    labelKey: 'footerExternalProtectedAreasLabel',
    icon: ExternalLink,
    requiresExitConfirm: true,
    visibility: 'always',
    order: 130,
  },
  {
    kind: 'external',
    id: 'daily-fire-report',
    section: 'help',
    href: 'https://www.argentina.gob.ar/reporte-diario-de-incendios',
    labelKey: 'footerExternalDailyReportLabel',
    icon: ExternalLink,
    requiresExitConfirm: true,
    visibility: 'always',
    order: 140,
  },
] as const

const NAVIGATION_ITEMS_BY_ID = new Map(NAVIGATION_ITEMS.map((item) => [item.id, item]))

type VisibleItemsOptions = {
  includeLockedPreviews?: boolean
}

function isVisibleForAuth(
  item: NavigationItem,
  isAuthenticated: boolean,
  includeLockedPreviews: boolean,
): boolean {
  if (item.visibility === 'always') return true
  if (item.visibility === 'auth_only') {
    if (isAuthenticated) return true
    return includeLockedPreviews && item.kind === 'internal' && item.guestPreview === 'locked'
  }
  return !isAuthenticated
}

export function isLockedPreview(item: NavigationItem, isAuthenticated: boolean): boolean {
  return (
    !isAuthenticated &&
    item.kind === 'internal' &&
    item.visibility === 'auth_only' &&
    item.guestPreview === 'locked'
  )
}

function isInternalFeatureEnabled(item: InternalNavigationItem): boolean {
  if (!item.featureFlag) return true
  return isFeatureEnabled(item.featureFlag)
}

function sortByOrder<T extends NavigationItem>(items: readonly T[]): T[] {
  return [...items].sort((a, b) => a.order - b.order)
}

export function getVisibleItems(
  section: NavigationSection,
  isAuthenticated: boolean,
  options: VisibleItemsOptions = {},
): NavigationItem[] {
  const includeLockedPreviews = options.includeLockedPreviews ?? false

  return sortByOrder(
    NAVIGATION_ITEMS.filter(
      (item) =>
        item.section === section &&
        isVisibleForAuth(item, isAuthenticated, includeLockedPreviews) &&
        (item.kind === 'external' || isInternalFeatureEnabled(item)),
    ),
  )
}

export function getVisibleItemsByIds(
  itemIds: readonly string[],
  isAuthenticated: boolean,
  options: VisibleItemsOptions = {},
): NavigationItem[] {
  const includeLockedPreviews = options.includeLockedPreviews ?? false

  return itemIds.flatMap((id) => {
    const item = NAVIGATION_ITEMS_BY_ID.get(id)
    if (!item) return []
    if (!isVisibleForAuth(item, isAuthenticated, includeLockedPreviews)) return []
    if (item.kind === 'internal' && !isInternalFeatureEnabled(item)) return []
    return [item]
  })
}

export function getSectionedItems(
  isAuthenticated: boolean,
): Record<NavigationSection, NavigationItem[]> {
  return {
    explore: getVisibleItems('explore', isAuthenticated),
    tools: getVisibleItems('tools', isAuthenticated),
    account: getVisibleItems('account', isAuthenticated),
    help: getVisibleItems('help', isAuthenticated),
  }
}

export function getInternalItems(items: readonly NavigationItem[]): InternalNavigationItem[] {
  return items.filter((item): item is InternalNavigationItem => item.kind === 'internal')
}

export function getExternalItems(items: readonly NavigationItem[]): ExternalNavigationItem[] {
  return items.filter((item): item is ExternalNavigationItem => item.kind === 'external')
}

export function navLinkShouldUseExactMatch(activeMatch: NavigationActiveMatch): boolean {
  return activeMatch === 'exact'
}

const PRIMARY_NAVIGATION_ITEM_IDS = new Set(['home', 'fires-history', 'map', 'audit', 'exploration'])

export const PRIMARY_NAVIGATION_ITEMS: readonly InternalNavigationItem[] = sortByOrder(
  getInternalItems(NAVIGATION_ITEMS).filter((item) => PRIMARY_NAVIGATION_ITEM_IDS.has(item.id)),
)
