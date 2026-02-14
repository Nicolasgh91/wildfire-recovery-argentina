import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import { ContactForm } from '@/components/contact/ContactForm'

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
  }),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

vi.mock('@/services/endpoints/contact', () => ({
  sendContactForm: vi.fn(),
}))

describe('ContactForm i18n', () => {
  it('shows English validation when language is en', async () => {
    localStorage.setItem('fg:language', 'en')
    const user = userEvent.setup()

    render(
      <I18nProvider>
        <ContactForm />
      </I18nProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Send Message' }))

    expect(screen.getByText('Name is required')).toBeTruthy()
  })
})
