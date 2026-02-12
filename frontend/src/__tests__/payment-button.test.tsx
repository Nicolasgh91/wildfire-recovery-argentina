import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { toast } from 'sonner'
import { I18nProvider } from '@/context/LanguageContext'
import { PaymentButton } from '@/components/payments/PaymentButton'

const createCheckoutMock = vi.fn()

vi.mock('sonner', () => {
  const toastMock = { error: vi.fn() }
  return { toast: toastMock }
})

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    status: 'unauthenticated',
    role: 'anonymous',
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signUpWithEmail: vi.fn(),
    signOut: vi.fn(),
    isAuthenticated: false,
  }),
}))

vi.mock('@/hooks/mutations/useCreateCheckout', () => ({
  useCreateCheckout: () => ({
    mutate: createCheckoutMock,
    isPending: false,
  }),
}))

describe('PaymentButton auth gating', () => {
  it('blocks checkout when unauthenticated', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <I18nProvider>
          <PaymentButton purpose="credits" creditsAmount={10}>
            Pagar
          </PaymentButton>
        </I18nProvider>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Pagar' }))

    expect(createCheckoutMock).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith('Inicia sesion para continuar.')
  })
})
