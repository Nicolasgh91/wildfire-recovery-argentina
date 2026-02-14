import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import NotFoundPage from '@/pages/NotFound'

describe('NotFoundPage', () => {
  it('renders a friendly message', () => {
    localStorage.setItem('fg:language', 'es')

    render(
      <MemoryRouter>
        <I18nProvider>
          <NotFoundPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText(/p[áa]gina no encontrada/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: /volver al inicio/i })).toBeTruthy()
  })
})
