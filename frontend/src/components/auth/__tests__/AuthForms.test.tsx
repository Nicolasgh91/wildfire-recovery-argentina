import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthFormOTP } from '../AuthFormOTP'
import { AuthFormEmail } from '../AuthFormEmail'
import { AuthFormOAuth } from '../AuthFormOAuth'
import { useAuth } from '@/context/AuthContext'

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockToastSuccess = vi.fn()
const mockToastError = vi.fn()
vi.mock('sonner', () => ({
  toast: {
    success: (...args: any[]) => mockToastSuccess(...args),
    error: (...args: any[]) => mockToastError(...args),
  },
}))

const mockSignIn = vi.fn()
const mockSignInWithGoogle = vi.fn()
const mockSignInWithOtp = vi.fn()

function renderAuthForms() {
  return render(
    <MemoryRouter>
      <div>
        <AuthFormOTP />
        <AuthFormEmail />
        <AuthFormOAuth />
      </div>
    </MemoryRouter>,
  )
}

describe('AuthForms', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue({
      signIn: mockSignIn,
      signInWithGoogle: mockSignInWithGoogle,
      signInWithOtp: mockSignInWithOtp,
      status: 'unauthenticated',
      isAuthenticated: false,
      user: null,
      session: null,
      role: 'anonymous',
      signOut: vi.fn(),
      signUpWithEmail: vi.fn(),
    })
  })

  it('renders OTP email input and submit button', () => {
    render(
      <MemoryRouter>
        <AuthFormOTP />
      </MemoryRouter>,
    )

    expect(screen.getByLabelText('email')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('shows OTP validation error on invalid email', async () => {
    render(
      <MemoryRouter>
        <AuthFormOTP />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    const input = screen.getByLabelText('email')
    await user.type(input, 'invalid-email')
    await user.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(screen.getByText('validationInvalidEmail')).toBeInTheDocument()
    })
  })

  it('submits OTP with valid email', async () => {
    render(
      <MemoryRouter>
        <AuthFormOTP />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('email'), 'test@example.com')
    await user.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(mockSignInWithOtp).toHaveBeenCalledWith('test@example.com')
      expect(mockToastSuccess).toHaveBeenCalledWith(expect.stringContaining('test@example.com'))
    })
  })

  it('calls signIn when email form is valid', async () => {
    render(
      <MemoryRouter>
        <AuthFormEmail />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('email'), 'test@example.com')
    await user.type(screen.getByLabelText('password'), 'secret123')
    await user.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'secret123')
    })
  })

  it('renders google button and calls signInWithGoogle', async () => {
    render(
      <MemoryRouter>
        <AuthFormOAuth />
      </MemoryRouter>,
    )

    const user = userEvent.setup()
    const button = screen.getByTestId('login-google')
    await user.click(button)

    expect(mockSignInWithGoogle).toHaveBeenCalled()
  })

  it('OTP loading stays local and does not disable email/google actions', async () => {
    mockSignInWithOtp.mockReturnValueOnce(new Promise(() => {}))
    renderAuthForms()

    const user = userEvent.setup()
    const otpForm = screen.getByTestId('auth-form-otp')
    const emailForm = screen.getByTestId('auth-form-email')

    await user.type(within(otpForm).getByLabelText('email'), 'otp@example.com')
    await user.click(within(otpForm).getByRole('button', { name: /enviar enlace/i }))

    await waitFor(() => {
      expect(within(otpForm).getByRole('button')).toBeDisabled()
    })

    expect(screen.getByTestId('login-google')).not.toBeDisabled()
    expect(within(emailForm).getByRole('button')).not.toBeDisabled()
  })

  it('Google loading stays local and does not disable OTP/email actions', async () => {
    mockSignInWithGoogle.mockReturnValueOnce(new Promise(() => {}))
    renderAuthForms()

    const user = userEvent.setup()
    const otpForm = screen.getByTestId('auth-form-otp')
    const emailForm = screen.getByTestId('auth-form-email')
    const googleButton = screen.getByTestId('login-google')

    await user.click(googleButton)

    await waitFor(() => {
      expect(googleButton).toBeDisabled()
    })

    expect(within(otpForm).getByRole('button')).not.toBeDisabled()
    expect(within(emailForm).getByRole('button')).not.toBeDisabled()
  })

  it('Email loading stays local and does not disable OTP/google actions', async () => {
    mockSignIn.mockReturnValueOnce(new Promise(() => {}))
    renderAuthForms()

    const user = userEvent.setup()
    const otpForm = screen.getByTestId('auth-form-otp')
    const emailForm = screen.getByTestId('auth-form-email')
    const emailSubmit = within(emailForm).getByRole('button')

    await user.type(within(emailForm).getByLabelText('email'), 'mail@example.com')
    await user.type(within(emailForm).getByLabelText('password'), 'secret123')
    await user.click(emailSubmit)

    await waitFor(() => {
      expect(emailSubmit).toBeDisabled()
    })

    expect(within(otpForm).getByRole('button')).not.toBeDisabled()
    expect(screen.getByTestId('login-google')).not.toBeDisabled()
  })
})