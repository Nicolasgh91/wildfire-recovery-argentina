import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { NavigationDrawer } from '@/features/navigation/components/navigation-drawer'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetTitle: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SheetDescription: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    language: 'es',
    setLanguage: vi.fn(),
    t: (key: string) =>
      (
        {
          navMenu: 'Menu',
          navPreferences: 'Preferencias',
          navMoreInformation: 'Más información',
          footerSupport: 'Soporte',
          footerPublicSources: 'Fuentes públicas',
        } as Record<string, string>
      )[key] ?? key,
  }),
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    role: 'anonymous',
    status: 'unauthenticated',
    isAuthenticated: false,
    signOut: vi.fn(),
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signInWithOtp: vi.fn(),
    signUpWithEmail: vi.fn(),
  }),
}))

vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: vi.fn(),
  }),
}))

vi.mock('@/features/navigation/components/navigation-menu-sections', () => ({
  NavigationMenuSections: ({
    sections,
    onLockedNavigate,
  }: {
    sections: string[]
    onLockedNavigate: (path: string) => void
  }) => (
    <div data-testid={`sections-${sections.join('-')}`}>
      <span>{`sections:${sections.join(',')}`}</span>
      {sections.includes('tools') && (
        <>
          <button type="button" onClick={() => onLockedNavigate('/audit')}>
            locked-audit
          </button>
          <button type="button" onClick={() => onLockedNavigate('/fires/history')}>
            locked-history
          </button>
        </>
      )}
    </div>
  ),
}))

vi.mock('@/features/navigation/components/navigation-drawer-collapsible-groups', () => ({
  NavigationDrawerCollapsibleGroups: () => (
    <div data-testid="drawer-collapsible-groups">collapsible-groups</div>
  ),
}))

vi.mock('@/features/navigation/components/external-confirm-dialog', () => ({
  ExternalConfirmDialog: () => null,
}))

vi.mock('@/features/account/components/logout-action', () => ({
  LogoutAction: () => null,
}))

describe('NavigationDrawer locked item behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('propagates locked intent and closes drawer', async () => {
    const onOpenChange = vi.fn()
    const onLockedItemIntent = vi.fn()

    render(
      <MemoryRouter>
        <NavigationDrawer
          open
          onOpenChange={onOpenChange}
          onLockedItemIntent={onLockedItemIntent}
        />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'locked-audit' }))
    await user.click(screen.getByRole('button', { name: 'locked-history' }))

    expect(onLockedItemIntent).toHaveBeenNthCalledWith(1, '/audit')
    expect(onLockedItemIntent).toHaveBeenNthCalledWith(2, '/fires/history')
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(onOpenChange).toHaveBeenCalledTimes(2)
  })

  it('keeps account section after collapsible groups and before preferences', () => {
    const onOpenChange = vi.fn()
    const { container } = render(
      <MemoryRouter>
        <NavigationDrawer
          open
          onOpenChange={onOpenChange}
          onLockedItemIntent={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('sections-explore-tools')).toBeInTheDocument()
    expect(screen.getByTestId('drawer-collapsible-groups')).toBeInTheDocument()
    expect(screen.getByTestId('sections-account')).toBeInTheDocument()
    expect(screen.getByText('Preferencias')).toBeInTheDocument()

    const fullText = container.textContent ?? ''
    const exploreToolsIndex = fullText.indexOf('sections:explore,tools')
    const collapsibleIndex = fullText.indexOf('collapsible-groups')
    const accountIndex = fullText.indexOf('sections:account')
    const preferencesIndex = fullText.indexOf('Preferencias')

    expect(exploreToolsIndex).toBeGreaterThan(-1)
    expect(collapsibleIndex).toBeGreaterThan(-1)
    expect(accountIndex).toBeGreaterThan(-1)
    expect(preferencesIndex).toBeGreaterThan(-1)
    expect(exploreToolsIndex).toBeLessThan(collapsibleIndex)
    expect(collapsibleIndex).toBeLessThan(accountIndex)
    expect(accountIndex).toBeLessThan(preferencesIndex)
  })
})
