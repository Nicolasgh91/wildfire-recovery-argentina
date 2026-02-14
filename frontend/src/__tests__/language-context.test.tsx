import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { I18nProvider, useI18n } from '@/context/LanguageContext'

function TestComponent() {
  const { t } = useI18n()
  return <span>{t('home')}</span>
}

function TestLanguageSwitch() {
  const { t, setLanguage } = useI18n()
  return (
    <div>
      <span>{t('paymentSuccessful')}</span>
      <button type="button" onClick={() => setLanguage('en')}>
        switch
      </button>
    </div>
  )
}

describe('I18nProvider', () => {
  it('provides default translations', () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>,
    )

    expect(screen.getByText('Inicio')).toBeTruthy()
  })

  it('switches language and resolves new translation keys', async () => {
    const user = userEvent.setup()

    render(
      <I18nProvider>
        <TestLanguageSwitch />
      </I18nProvider>,
    )

    expect(screen.getByText('¡Pago exitoso!')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'switch' }))
    expect(screen.getByText('Payment successful!')).toBeTruthy()
  })
})
