import { render, screen } from '@testing-library/react'
import { I18nProvider, useI18n } from '@/context/LanguageContext'

function TestComponent() {
  const { t } = useI18n()
  return <span>{t('home')}</span>
}

describe('I18nProvider', () => {
  it('provides default translations', () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>,
    )

    expect(screen.getByText('Inicio')).toBeInTheDocument()
  })
})
