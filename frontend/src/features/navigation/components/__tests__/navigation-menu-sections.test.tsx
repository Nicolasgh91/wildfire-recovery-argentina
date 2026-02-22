import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { NavigationMenuSections } from '@/features/navigation/components/navigation-menu-sections'

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        navTools: 'Herramientas',
        fireHistory: 'Historicos',
        audit: 'Verificar terreno',
      })[key] ?? key,
  }),
}))

describe('NavigationMenuSections locked previews', () => {
  it('renders audit and history as locked items for guests when includeLockedPreviews is enabled', () => {
    render(
      <MemoryRouter>
        <NavigationMenuSections
          sections={['tools']}
          isAuthenticated={false}
          includeLockedPreviews
          onInternalNavigate={vi.fn()}
          onLockedNavigate={vi.fn()}
          onExternalClick={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('button', { name: /Verificar terreno - requiere inicio de sesion/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Historicos - requiere inicio de sesion/i }),
    ).toBeInTheDocument()
  })

  it('routes locked item clicks through onLockedNavigate callback', async () => {
    const onLockedNavigate = vi.fn()

    render(
      <MemoryRouter>
        <NavigationMenuSections
          sections={['tools']}
          isAuthenticated={false}
          includeLockedPreviews
          onInternalNavigate={vi.fn()}
          onLockedNavigate={onLockedNavigate}
          onExternalClick={vi.fn()}
        />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.click(
      screen.getByRole('button', { name: /Verificar terreno - requiere inicio de sesion/i }),
    )
    await user.click(
      screen.getByRole('button', { name: /Historicos - requiere inicio de sesion/i }),
    )

    expect(onLockedNavigate).toHaveBeenNthCalledWith(1, '/audit')
    expect(onLockedNavigate).toHaveBeenNthCalledWith(2, '/fires/history')
  })
})
