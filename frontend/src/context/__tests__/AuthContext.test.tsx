import { act, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '../AuthContext'
import { supabase } from '@/lib/supabase'
import { setAuthToken } from '@/services/api'
import { touchIdleActivity, clearIdleActivity } from '@/lib/idleActivity'

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      signInWithOAuth: vi.fn(),
      signInWithOtp: vi.fn(),
    },
  },
}))

vi.mock('@/services/api', () => ({
  setAuthToken: vi.fn(),
}))

vi.mock('@/lib/idleActivity', () => ({
  touchIdleActivity: vi.fn(),
  clearIdleActivity: vi.fn(),
}))

function AuthStateProbe() {
  const { status, user, isAuthenticated } = useAuth()
  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="is-auth">{isAuthenticated ? 'yes' : 'no'}</div>
      {user && <div data-testid="user-email">{user.email}</div>}
    </div>
  )
}

function AuthActionsProbe() {
  const { signIn, signInWithGoogle, signInWithOtp, signOut, signUpWithEmail } = useAuth()

  return (
    <div>
      <button type="button" onClick={() => void signIn('user@example.com', 'secret123')}>
        sign-in
      </button>
      <button type="button" onClick={() => void signInWithGoogle()}>
        sign-in-google
      </button>
      <button type="button" onClick={() => void signInWithOtp('otp@example.com')}>
        sign-in-otp
      </button>
      <button
        type="button"
        onClick={() =>
          void signUpWithEmail({
            email: 'signup@example.com',
            firstName: 'Jane',
            lastName: 'Doe',
          })
        }
      >
        sign-up
      </button>
      <button type="button" onClick={() => void signOut()}>
        sign-out
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    } as any)

    vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    } as any)

    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValue({ error: null } as any)
    vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValue({ error: null } as any)
    vi.mocked(supabase.auth.signInWithOtp).mockResolvedValue({ error: null } as any)
    vi.mocked(supabase.auth.signOut).mockResolvedValue({ error: null } as any)
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('initially renders loading state and resolves to unauthenticated', async () => {
    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    )

    expect(screen.getByTestId('status')).toHaveTextContent('loading')
    expect(screen.getByTestId('is-auth')).toHaveTextContent('no')

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated')
    })

    expect(setAuthToken).toHaveBeenCalledWith(null)
    expect(clearIdleActivity).toHaveBeenCalled()
  })

  it('authenticates when getSession returns a session', async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValueOnce({
      data: {
        session: {
          user: { email: 'test@example.com', app_metadata: { role: 'user' } },
          access_token: 'mock-token',
        },
      },
      error: null,
    } as any)

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('authenticated')
    })

    expect(screen.getByTestId('is-auth')).toHaveTextContent('yes')
    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com')
    expect(setAuthToken).toHaveBeenCalledWith('mock-token')
    expect(touchIdleActivity).toHaveBeenCalled()
  })

  it('updates state when onAuthStateChange emits SIGNED_IN', async () => {
    let stateChangeCallback: ((event: string, session: any) => void) | undefined

    vi.mocked(supabase.auth.onAuthStateChange).mockImplementation((callback: any) => {
      stateChangeCallback = callback
      return { data: { subscription: { unsubscribe: vi.fn() } } } as any
    })

    render(
      <AuthProvider>
        <AuthStateProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated')
    })

    act(() => {
      stateChangeCallback?.('SIGNED_IN', {
        user: { email: 'new@example.com', app_metadata: { role: 'user' } },
        access_token: 'new-token',
      })
    })

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('authenticated')
      expect(screen.getByTestId('user-email')).toHaveTextContent('new@example.com')
    })
  })

  it('invokes Supabase auth methods through the public context API', async () => {
    render(
      <AuthProvider>
        <AuthActionsProbe />
      </AuthProvider>,
    )

    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'sign-in' }))
    await user.click(screen.getByRole('button', { name: 'sign-in-google' }))
    await user.click(screen.getByRole('button', { name: 'sign-in-otp' }))
    await user.click(screen.getByRole('button', { name: 'sign-up' }))
    await user.click(screen.getByRole('button', { name: 'sign-out' }))

    await waitFor(() => {
      expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'secret123',
      })
    })

    expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith({
      provider: 'google',
      options: {
        redirectTo: expect.stringContaining('/auth/callback'),
      },
    })

    expect(supabase.auth.signInWithOtp).toHaveBeenCalledWith({
      email: 'otp@example.com',
      options: {
        emailRedirectTo: expect.stringContaining('/auth/callback'),
      },
    })

    expect(supabase.auth.signInWithOtp).toHaveBeenCalledWith({
      email: 'signup@example.com',
      options: {
        data: {
          full_name: 'Jane Doe',
          first_name: 'Jane',
          last_name: 'Doe',
        },
        emailRedirectTo: expect.stringContaining('/auth/callback'),
      },
    })

    expect(supabase.auth.signOut).toHaveBeenCalledTimes(1)
  })
})
