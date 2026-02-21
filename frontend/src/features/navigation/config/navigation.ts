import { ClipboardCheck, FileText, Flame, Map, Trees, type LucideIcon } from 'lucide-react'
import type { TranslationKey } from '@/data/translations'
import { HOME_PATH } from '@/lib/routing'

export type NavigationActiveMatch = 'exact' | 'prefix'

export interface InternalNavigationItem {
  to: string
  labelKey: TranslationKey
  icon: LucideIcon
  activeMatch: NavigationActiveMatch
}

export const PRIMARY_NAVIGATION_ITEMS: readonly InternalNavigationItem[] = [
  {
    to: HOME_PATH,
    labelKey: 'home',
    icon: Trees,
    activeMatch: 'exact',
  },
  {
    to: '/fires/history',
    labelKey: 'fireHistory',
    icon: Flame,
    // Keep the parent item active when navigating to dynamic descendants.
    activeMatch: 'prefix',
  },
  {
    to: '/map',
    labelKey: 'map',
    icon: Map,
    activeMatch: 'exact',
  },
  {
    to: '/audit',
    labelKey: 'audit',
    icon: ClipboardCheck,
    activeMatch: 'exact',
  },
  {
    to: '/exploracion',
    labelKey: 'reports',
    icon: FileText,
    activeMatch: 'exact',
  },
] as const

export function navLinkShouldUseExactMatch(activeMatch: NavigationActiveMatch): boolean {
  return activeMatch === 'exact'
}

