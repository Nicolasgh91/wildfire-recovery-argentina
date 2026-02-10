import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { AuthProvider, useAuth } from '@/context/AuthContext'

const listeners = new Set<(event: string, session: any) => void>()
let currentSession: any = null

const emitAuthChange = (event: string, session: any) => {
  listeners.forEach((callback) => callback(event, session))
}

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({ data: { session: currentSession } })),
      onAuthStateChange: vi.fn((callback: (event: string, session: any) => void) => {
        listeners.add(callback)
        return {
          data: {
            subscription: {
              unsubscribe: () => listeners.delete(callback),
            },
          },
        }
      }),
      signInWithPassword: vi.fn(async ({ email }: { email: string }) => {
        currentSession = {
          user: {
            email,
            app_metadata: { role: email.includes('admin') ? 'admin' : 'user' },
          },
        }
        emitAuthChange('SIGNED_IN', currentSession)
        return { data: { session: currentSession }, error: null }
      }),
      signOut: vi.fn(async () => {
        currentSession = null
        emitAuthChange('SIGNED_OUT', null)
        return { error: null }
      }),
    },
  },
}))

function AuthTester() {
  const { user, role, isAuthenticated, signIn, signOut } = useAuth()

  return (
    <div>
      <span data-testid="role">{role}</span>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <button type="button" onClick={() => signIn('admin@forestguard.ar', 'pass')}>
        login-admin
      </button>
      <button type="button" onClick={() => signIn('user@example.com', 'pass')}>
        login-user
      </button>
      <button type="button" onClick={signOut}>
        logout
      </button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    currentSession = null
    listeners.clear()
  })

  it('handles login and logout flow', async () => {
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <AuthTester />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth')).toHaveTextContent('no')
    })
    expect(screen.getByTestId('role')).toHaveTextContent('anonymous')
    expect(screen.getByTestId('email')).toHaveTextContent('none')

    await user.click(screen.getByRole('button', { name: 'login-admin' }))
    await waitFor(() => {
      expect(screen.getByTestId('auth')).toHaveTextContent('yes')
    })
    expect(screen.getByTestId('role')).toHaveTextContent('admin')
    expect(screen.getByTestId('email')).toHaveTextContent('admin@forestguard.ar')

    await user.click(screen.getByRole('button', { name: 'logout' }))
    await waitFor(() => {
      expect(screen.getByTestId('auth')).toHaveTextContent('no')
    })
    expect(screen.getByTestId('role')).toHaveTextContent('anonymous')
  })

  it('assigns user role for non-admin emails', async () => {
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <AuthTester />
      </AuthProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'login-user' }))
    await waitFor(() => {
      expect(screen.getByTestId('role')).toHaveTextContent('user')
    })
    expect(screen.getByTestId('email')).toHaveTextContent('user@example.com')
  })
})
