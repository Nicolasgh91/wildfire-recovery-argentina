import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotFoundPage from '@/pages/NotFound'

describe('NotFoundPage', () => {
  it('renders a friendly message', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Page not found')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /back to home/i }),
    ).toBeInTheDocument()
  })
})
