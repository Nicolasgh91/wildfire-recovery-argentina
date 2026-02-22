import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Navbar } from '@/components/layout/navbar'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    language: 'es',
    setLanguage: vi.fn(),
    t: (key: string) =>
      (
        {
          home: 'Inicio',
          map: 'Mapa',
          reports: 'Exploracion satelital',
          audit: 'Verificar terreno',
          fireHistory: 'Historicos',
          protectedPageTitle: 'Acceso restringido',
          protectedPageMessage:
            'Esta pagina es exclusiva para usuarios registrados. Por favor, inicia sesion para continuar.',
          goBack: 'Volver atras',
          login: 'Iniciar sesion',
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

vi.mock('@/features/navigation/components/navigation-bottom-nav', () => ({
  NavigationBottomNav: () => <div data-testid="bottom-nav" />,
}))

vi.mock('@/features/navigation/components/navigation-topbar-tablet', () => ({
  NavigationTopbarTablet: () => <div data-testid="topbar-tablet" />,
}))

vi.mock('@/features/navigation/components/navigation-drawer', () => ({
  NavigationDrawer: () => null,
}))

describe('Navbar locked previews', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows restricted modal for locked items and routes actions correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <Navbar />
      </MemoryRouter>,
    )

    const user = userEvent.setup()

    await user.click(
      screen.getByRole('button', { name: /Verificar terreno - requiere inicio de sesion/i }),
    )

    expect(mockNavigate).not.toHaveBeenCalled()
    expect(screen.getByText('Acceso restringido')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Volver atras' }))
    expect(mockNavigate).not.toHaveBeenCalled()
    expect(screen.queryByText('Acceso restringido')).not.toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: /Verificar terreno - requiere inicio de sesion/i }),
    )
    await user.click(screen.getByRole('button', { name: 'Iniciar sesion' }))

    expect(mockNavigate).toHaveBeenCalledWith('/login', {
      state: { from: { pathname: '/audit' }, reason: 'nav_locked_item' },
    })
  })
})
