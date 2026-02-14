import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { I18nProvider, useI18n } from '@/context/LanguageContext'
import ManualPage from '@/pages/manual'

function ManualWithLanguageSwitch() {
  const { setLanguage } = useI18n()

  return (
    <>
      <button type="button" onClick={() => setLanguage('en')}>
        switch
      </button>
      <ManualPage />
    </>
  )
}

describe('ManualPage i18n', () => {
  it('switches from Spanish to English labels', async () => {
    localStorage.setItem('fg:language', 'es')
    const user = userEvent.setup()

    render(
      <I18nProvider>
        <ManualWithLanguageSwitch />
      </I18nProvider>,
    )

    expect(screen.getByText('Manual de Usuario')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'switch' }))
    expect(screen.getByText('User Manual')).toBeTruthy()
  })
})
