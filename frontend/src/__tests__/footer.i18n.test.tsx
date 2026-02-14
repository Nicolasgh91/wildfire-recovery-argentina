import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import { Footer } from '@/components/layout/footer'

describe('Footer i18n', () => {
  it('renders English labels when language is en', () => {
    localStorage.setItem('fg:language', 'en')

    render(
      <MemoryRouter>
        <I18nProvider>
          <Footer />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText('Product')).toBeTruthy()
    expect(screen.getByText('Public sources')).toBeTruthy()
    expect(screen.getByText('User Manual')).toBeTruthy()
  })
})
