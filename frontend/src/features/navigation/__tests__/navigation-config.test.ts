import { describe, expect, it } from 'vitest'
import {
  getVisibleItemsByIds,
  getSectionedItems,
  getVisibleItems,
  isLockedPreview,
  type NavigationItem,
} from '@/features/navigation/config/navigation'

function ids(items: NavigationItem[]): string[] {
  return items.map((item) => item.id)
}

describe('navigation config visibility', () => {
  it('shows login for guests and hides profile', () => {
    const accountItems = getVisibleItems('account', false)
    expect(ids(accountItems)).toContain('login')
    expect(ids(accountItems)).not.toContain('profile')
  })

  it('keeps auth-only tools hidden for guests by default', () => {
    const toolsItems = getVisibleItems('tools', false)
    expect(ids(toolsItems)).not.toContain('audit')
    expect(ids(toolsItems)).not.toContain('fires-history')
  })

  it('shows locked previews for auth-only tools when includeLockedPreviews is enabled', () => {
    const toolsItems = getVisibleItems('tools', false, { includeLockedPreviews: true })
    const toolIds = ids(toolsItems)
    expect(toolIds).toContain('audit')
    expect(toolIds).toContain('fires-history')

    const auditItem = toolsItems.find((item) => item.id === 'audit')
    const historyItem = toolsItems.find((item) => item.id === 'fires-history')
    expect(auditItem).toBeDefined()
    expect(historyItem).toBeDefined()
    expect(isLockedPreview(auditItem!, false)).toBe(true)
    expect(isLockedPreview(historyItem!, false)).toBe(true)
  })

  it('shows profile for authenticated users and hides login', () => {
    const accountItems = getVisibleItems('account', true)
    expect(ids(accountItems)).toContain('profile')
    expect(ids(accountItems)).not.toContain('login')
  })

  it('renders auth-only tools as normal items for authenticated users', () => {
    const toolsItems = getVisibleItems('tools', true, { includeLockedPreviews: true })
    expect(ids(toolsItems)).toContain('audit')
    expect(ids(toolsItems)).toContain('fires-history')

    const auditItem = toolsItems.find((item) => item.id === 'audit')
    const historyItem = toolsItems.find((item) => item.id === 'fires-history')
    expect(isLockedPreview(auditItem!, true)).toBe(false)
    expect(isLockedPreview(historyItem!, true)).toBe(false)
  })

  it('exposes explore/tools/help sections with deterministic order', () => {
    const sectioned = getSectionedItems(true)
    expect(ids(sectioned.explore)).toEqual(['home', 'map', 'exploration'])
    expect(ids(sectioned.help)).toEqual([
      'faq',
      'manual',
      'glossary',
      'contact',
      'api-docs',
      'protected-areas',
      'daily-fire-report',
    ])
  })

  it('resolves visibility by explicit id order', () => {
    const ordered = getVisibleItemsByIds(
      ['contact', 'faq', 'manual', 'audit', 'daily-fire-report'],
      false,
    )
    expect(ids(ordered)).toEqual(['contact', 'faq', 'manual', 'daily-fire-report'])
  })

  it('supports locked previews when resolving by ids', () => {
    const ordered = getVisibleItemsByIds(
      ['home', 'audit', 'fires-history'],
      false,
      { includeLockedPreviews: true },
    )
    expect(ids(ordered)).toEqual(['home', 'audit', 'fires-history'])
    expect(isLockedPreview(ordered[1], false)).toBe(true)
    expect(isLockedPreview(ordered[2], false)).toBe(true)
  })
})
