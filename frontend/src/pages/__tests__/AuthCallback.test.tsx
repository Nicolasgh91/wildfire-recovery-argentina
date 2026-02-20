import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AuthCallbackPage from '../AuthCallback'
import { supabase } from '@/lib/supabase'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
    },
  },
}))

const mockGetSession = vi.mocked(supabase.auth.getSession)
const mockOnAuthStateChange = vi.mocked(supabase.auth.onAuthStateChange)

describe('AuthCallbackPage', () => {
  let authStateListener: ((event: string, session: any) => void) | undefined

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    sessionStorage.clear()
    window.history.replaceState({}, '', '/auth/callback')

    authStateListener = undefined
    mockOnAuthStateChange.mockImplementation((callback: any) => {
      authStateListener = callback
      return {
        data: {
          subscription: {
            unsubscribe: vi.fn(),
          },
        },
      } as any
    })

    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    } as any)
  })

  it('navigates to returnTo when onAuthStateChange receives a session', async () => {
    sessionStorage.setItem('auth:returnTo', '/map')

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    act(() => {
      authStateListener?.('SIGNED_IN', {
        access_token: 'token',
        user: { id: 'user-id', email: 'test@example.com' },
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/map', { replace: true })
    })

    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('uses getSession as fallback when session already exists', async () => {
    sessionStorage.setItem('auth:returnTo', '/fires/123')
    mockGetSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: 'existing-token',
          user: { id: 'user-id', email: 'test@example.com' },
        },
      },
      error: null,
    } as any)

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/fires/123', { replace: true })
    })

    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('falls back to /home when returnTo is missing', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: 'existing-token',
          user: { id: 'user-id', email: 'test@example.com' },
        },
      },
      error: null,
    } as any)

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/home', { replace: true })
    })
  })

  it('supports PKCE callback URL with code query param', async () => {
    sessionStorage.setItem('auth:returnTo', '/profile')
    window.history.replaceState({}, '', '/auth/callback?code=pkce_code_123')

    mockGetSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: 'pkce-token',
          user: { id: 'user-id', email: 'test@example.com' },
        },
      },
      error: null,
    } as any)

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/profile', { replace: true })
    })
  })

  it('supports PKCE callback with code while session arrives via auth event', async () => {
    sessionStorage.setItem('auth:returnTo', '/exploracion')
    window.history.replaceState({}, '', '/auth/callback?code=pkce_code_456')

    mockGetSession.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    } as any)

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    act(() => {
      authStateListener?.('SIGNED_IN', {
        access_token: 'pkce-event-token',
        user: { id: 'user-id', email: 'test@example.com' },
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/exploracion', { replace: true })
    })
  })

  it('redirects to login when OAuth is cancelled by user (access_denied)', async () => {
    sessionStorage.setItem('auth:returnTo', '/map')
    window.history.replaceState(
      {},
      '',
      '/auth/callback?error=access_denied&error_description=Usuario%20denegado',
    )

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', {
        replace: true,
        state: { cancelled: true },
      })
    })

    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('shows permanent error state when URL contains non-transient auth error', async () => {
    sessionStorage.setItem('auth:returnTo', '/map')
    window.history.replaceState(
      {},
      '',
      '/auth/callback?error=invalid_scope&error_description=Permisos%20insuficientes',
    )

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('No se pudo completar el login')).toBeInTheDocument()
    expect(screen.getByText('Permisos insuficientes')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('shows transient timeout state after 20 seconds and allows retry', async () => {
    vi.useFakeTimers()
    sessionStorage.setItem('auth:returnTo', '/map')

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    await act(async () => {
      vi.advanceTimersByTime(10_000)
      await Promise.resolve()
    })

    expect(screen.getByText('Todavia estamos procesando el inicio de sesion...')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(10_000)
      await Promise.resolve()
    })

    expect(screen.getByText('No se pudo completar el login')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ir a login' })).toBeInTheDocument()
    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()

    await act(async () => {
      screen.getByRole('button', { name: 'Reintentar' }).click()
    })

    expect(mockOnAuthStateChange).toHaveBeenCalledTimes(2)
  })

  it('navigates once when auth event fires multiple times', async () => {
    sessionStorage.setItem('auth:returnTo', '/map')

    render(
      <MemoryRouter>
        <AuthCallbackPage />
      </MemoryRouter>,
    )

    act(() => {
      const session = {
        access_token: 'token',
        user: { id: 'user-id', email: 'test@example.com' },
      }
      authStateListener?.('SIGNED_IN', session)
      authStateListener?.('TOKEN_REFRESHED', session)
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledTimes(1)
    })
  })
})
