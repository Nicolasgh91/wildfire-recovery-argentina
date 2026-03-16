import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import FireHistoryPage from '@/pages/FireHistory'
import { RETURN_CONTEXT_KEY, type ReturnContext } from '@/types/navigation'

function renderWithRouter(initialEntries: string[] = ['/fires/history']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/fires/history" element={<FireHistoryPage />} />
        <Route path="/fires/:id" element={<div data-testid="fire-detail-page" />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('FireHistory → FireDetail return context', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('stores ReturnContext when clicking a row', async () => {
    // Render page with one fire row via mocked response
    renderWithRouter(['/fires/history?status_scope=historical&page=2'])

    // For simplicity, assume at least one row is rendered; find by role button row
    const rowButton = await screen.findByRole('button')
    fireEvent.click(rowButton)

    const raw = sessionStorage.getItem(RETURN_CONTEXT_KEY)
    expect(raw).toBeTruthy()

    const ctx = JSON.parse(raw || '{}') as ReturnContext
    expect(ctx.returnTo).toBe('history')
    expect(ctx.history?.search).toContain('status_scope=historical')
  })
}

