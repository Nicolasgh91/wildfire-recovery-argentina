import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/context/LanguageContext'
import HomePage from '@/pages/Home'

const mockUseEpisodesByMode = vi.fn()

vi.mock('@/hooks/queries/useEpisodesByMode', () => ({
  useEpisodesByMode: (mode: string) => mockUseEpisodesByMode(mode),
}))

vi.mock('@/services/endpoints/episodes', () => ({
  getEpisodes: vi.fn().mockResolvedValue({ episodes: [] }),
}))

vi.mock('@/components/stories-bar', () => ({
  StoriesBar: () => <div data-testid="stories-bar" />,
}))

vi.mock('@/components/fire-filters', () => ({
  FireFilters: () => <div data-testid="fire-filters" />,
}))

vi.mock('@/components/fires/fire-card', () => ({
  FireCard: ({ fire }: { fire: { id: string } }) => (
    <div data-testid="fire-card">{fire.id}</div>
  ),
  FireCardSkeleton: () => <div data-testid="fire-card-skeleton" />,
}))

beforeAll(() => {
  class IO {
    callback: IntersectionObserverCallback
    constructor(callback: IntersectionObserverCallback) {
      this.callback = callback
    }
    observe() {
      this.callback([{ isIntersecting: true }] as IntersectionObserverEntry[], this)
    }
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(global, 'IntersectionObserver', {
    writable: true,
    value: IO,
  })
})

const renderHome = () =>
  render(
    <MemoryRouter>
      <I18nProvider>
        <HomePage />
      </I18nProvider>
    </MemoryRouter>,
  )

describe('Home recent toggle', () => {
  beforeEach(() => {
    mockUseEpisodesByMode.mockReset()
  })

  it('combina activos y recientes cuando se activa el toggle', async () => {
    const user = userEvent.setup()
    const active = [{ id: 'active-1', provinces: ['Chubut'] }]
    const recent = [{ id: 'recent-1', provinces: ['Chubut'] }]

    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: { episodes: mode === 'active' ? active : recent },
      isLoading: false,
    }))

    renderHome()

    await waitFor(() => {
      expect(screen.getAllByTestId('fire-card').length).toBe(1)
    })

    const toggle = document.getElementById('show-recents')
    expect(toggle).toBeTruthy()

    await user.click(toggle as HTMLElement)

    await waitFor(() => {
      expect(screen.getAllByTestId('fire-card').length).toBe(2)
    })
  })

  it('muestra recientes cuando no hay activos', async () => {
    const recent = [{ id: 'recent-1', provinces: ['Chubut'] }]

    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: { episodes: mode === 'active' ? [] : recent },
      isLoading: false,
    }))

    renderHome()

    await waitFor(() => {
      expect(screen.getAllByTestId('fire-card').length).toBe(1)
    })
    expect(screen.queryByText('Ver recientes')).not.toBeInTheDocument()
  })

  it('muestra empty state si no hay activos ni recientes', async () => {
    mockUseEpisodesByMode.mockImplementation(() => ({
      data: { episodes: [] },
      isLoading: false,
    }))

    renderHome()

    await waitFor(() => {
      expect(screen.getByText(/No hay incendios activos ni recientes/i)).toBeInTheDocument()
    })
  })
})
