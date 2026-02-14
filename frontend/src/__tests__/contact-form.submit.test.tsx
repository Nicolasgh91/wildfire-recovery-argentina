import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import { ContactForm } from '@/components/contact/ContactForm'

const sendContactFormMock = vi.fn()
const toastMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
  }),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: toastMock,
  }),
}))

vi.mock('@/services/endpoints/contact', () => ({
  sendContactForm: (...args: unknown[]) => sendContactFormMock(...args),
}))

describe('ContactForm submit failures', () => {
  beforeAll(() => {
    if (!Element.prototype.hasPointerCapture) {
      Element.prototype.hasPointerCapture = () => false
    }
    if (!Element.prototype.setPointerCapture) {
      Element.prototype.setPointerCapture = () => undefined
    }
    if (!Element.prototype.releasePointerCapture) {
      Element.prototype.releasePointerCapture = () => undefined
    }
    if (!Element.prototype.scrollIntoView) {
      Element.prototype.scrollIntoView = () => undefined
    }
  })

  beforeEach(() => {
    localStorage.setItem('fg:language', 'en')
    sendContactFormMock.mockReset()
    toastMock.mockReset()
  })

  it('shows error toast and re-enables submit button when API returns an error', async () => {
    sendContactFormMock.mockRejectedValueOnce(new Error('503'))
    const user = userEvent.setup()

    render(
      <I18nProvider>
        <ContactForm />
      </I18nProvider>,
    )

    await user.type(screen.getByLabelText(/first name/i), 'Juan')
    await user.type(screen.getByLabelText(/email/i), 'juan@example.com')
    await user.click(screen.getByRole('combobox'))
    await user.click(await screen.findByRole('option', { name: 'Technical Support' }))
    await user.type(
      screen.getByLabelText(/description/i),
      'Mensaje de prueba suficientemente largo.',
    )

    await user.click(screen.getByRole('button', { name: 'Send Message' }))

    await waitFor(() => expect(sendContactFormMock).toHaveBeenCalledTimes(1))
    await waitFor(() =>
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Error sending message',
          variant: 'destructive',
        }),
      ),
    )
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Send Message' })).not.toBeDisabled(),
    )
  })
})
