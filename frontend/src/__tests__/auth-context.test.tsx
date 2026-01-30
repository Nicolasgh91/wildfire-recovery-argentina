import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from '@/context/AuthContext'

function AuthTester() {
  const { user, role, isAuthenticated, login, logout } = useAuth()

  return (
    <div>
      <span data-testid="role">{role}</span>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="email">{user?.email ?? 'none'}</span>
      <button type="button" onClick={() => login('admin@forestguard.ar', 'pass')}>
        login-admin
      </button>
      <button type="button" onClick={() => login('user@example.com', 'pass')}>
        login-user
      </button>
      <button type="button" onClick={logout}>
        logout
      </button>
    </div>
  )
}

describe('AuthProvider', () => {
  it('handles login and logout flow', async () => {
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <AuthTester />
      </AuthProvider>,
    )

    expect(screen.getByTestId('auth')).toHaveTextContent('no')
    expect(screen.getByTestId('role')).toHaveTextContent('guest')
    expect(screen.getByTestId('email')).toHaveTextContent('none')

    await user.click(screen.getByRole('button', { name: 'login-admin' }))
    expect(screen.getByTestId('auth')).toHaveTextContent('yes')
    expect(screen.getByTestId('role')).toHaveTextContent('admin')
    expect(screen.getByTestId('email')).toHaveTextContent('admin@forestguard.ar')

    await user.click(screen.getByRole('button', { name: 'logout' }))
    expect(screen.getByTestId('auth')).toHaveTextContent('no')
    expect(screen.getByTestId('role')).toHaveTextContent('guest')
  })

  it('assigns user role for non-admin emails', async () => {
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <AuthTester />
      </AuthProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'login-user' }))
    expect(screen.getByTestId('role')).toHaveTextContent('user')
    expect(screen.getByTestId('email')).toHaveTextContent('user@example.com')
  })
})
