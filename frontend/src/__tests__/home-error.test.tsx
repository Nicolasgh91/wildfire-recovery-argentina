import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/context/LanguageContext'
import HomePage from '@/pages/Home'

const mockUseEpisodesByMode = vi.fn()

vi.mock('@/hooks/queries/useEpisodesByMode', () => ({
  useEpisodesByMode: (...args: unknown[]) => mockUseEpisodesByMode(...args),
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
      this.callback(
        [{ isIntersecting: true }] as IntersectionObserverEntry[],
        this as unknown as IntersectionObserver,
      )
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

describe('Home error state', () => {
  beforeEach(() => {
    mockUseEpisodesByMode.mockReset()
  })

  it('shows error banner when active query fails', async () => {
    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: undefined,
      isLoading: false,
      isError: mode === 'active',
      refetch: vi.fn(),
    }))

    renderHome()

    await waitFor(() => {
      expect(screen.getByText(/Error al cargar incendios/i)).toBeInTheDocument()
    })

    // Skeleton should NOT be visible when error is shown
    expect(screen.queryByTestId('fire-card-skeleton')).not.toBeInTheDocument()
  })

  it('shows retry button that triggers refetch', async () => {
    const user = userEvent.setup()
    const refetchActive = vi.fn()
    const refetchRecent = vi.fn()

    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: mode === 'active' ? refetchActive : refetchRecent,
    }))

    renderHome()

    const retryButton = await screen.findByText('Reintentar')
    await user.click(retryButton)

    expect(refetchActive).toHaveBeenCalled()
  })

  it('does not show error banner during loading', async () => {
    mockUseEpisodesByMode.mockImplementation(() => ({
      data: undefined,
      isLoading: true,
      isError: true,
      refetch: vi.fn(),
    }))

    renderHome()

    await waitFor(() => {
      expect(screen.queryByText(/Error al cargar incendios/i)).not.toBeInTheDocument()
    })
  })
})
