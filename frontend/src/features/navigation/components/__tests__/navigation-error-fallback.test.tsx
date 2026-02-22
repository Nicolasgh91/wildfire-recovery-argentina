import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { JSX } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { NavigationErrorBoundary } from '@/features/navigation/components/navigation-error-boundary'
import { NavigationErrorFallback } from '@/features/navigation/components/navigation-error-fallback'
import { useAuth } from '@/context/AuthContext'

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function ThrowingNav(): JSX.Element {
  throw new Error('navigation exploded')
}

describe('NavigationErrorFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders minimum operational links (home/map/login) when unauthenticated', () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      signOut: vi.fn(),
      status: 'unauthenticated',
      user: null,
      session: null,
      role: 'anonymous',
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
      signInWithOtp: vi.fn(),
      signUpWithEmail: vi.fn(),
    })

    render(
      <MemoryRouter>
        <NavigationErrorFallback />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Inicio' })).toHaveAttribute('href', '/home')
    expect(screen.getByRole('link', { name: 'Mapa' })).toHaveAttribute('href', '/map')
    expect(screen.getByRole('link', { name: 'Iniciar sesion' })).toHaveAttribute('href', '/login')
  })

  it('shows logout action and executes signOut when authenticated', async () => {
    const signOut = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      signOut,
      status: 'authenticated',
      user: { email: 'qa@example.com' } as any,
      session: {} as any,
      role: 'user',
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
      signInWithOtp: vi.fn(),
      signUpWithEmail: vi.fn(),
    })

    render(
      <MemoryRouter>
        <NavigationErrorFallback />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Cerrar sesion' }))

    await waitFor(() => {
      expect(signOut).toHaveBeenCalledTimes(1)
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  it('switches to the operational fallback when a navigation component throws', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      signOut: vi.fn(),
      status: 'unauthenticated',
      user: null,
      session: null,
      role: 'anonymous',
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
      signInWithOtp: vi.fn(),
      signUpWithEmail: vi.fn(),
    })

    render(
      <MemoryRouter>
        <NavigationErrorBoundary>
          <ThrowingNav />
        </NavigationErrorBoundary>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Inicio' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Mapa' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Iniciar sesion' })).toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })
})

