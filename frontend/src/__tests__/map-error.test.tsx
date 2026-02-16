import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/context/LanguageContext'
import MapPage from '@/pages/MapPage'

const mockUseEpisodesByMode = vi.fn()

vi.mock('@/hooks/queries/useEpisodesByMode', () => ({
  useEpisodesByMode: (...args: unknown[]) => mockUseEpisodesByMode(...args),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="fire-map" />,
}))

const renderMap = () =>
  render(
    <MemoryRouter>
      <I18nProvider>
        <MapPage />
      </I18nProvider>
    </MemoryRouter>,
  )

describe('MapPage error state', () => {
  beforeEach(() => {
    mockUseEpisodesByMode.mockReset()
  })

  it('shows error banner in sidebar when queries fail', async () => {
    mockUseEpisodesByMode.mockImplementation(() => ({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    }))

    renderMap()

    await waitFor(() => {
      expect(
        screen.getByText(/No pudimos obtener los datos/i),
      ).toBeInTheDocument()
    })
  })

  it('does not show empty state when in error state', async () => {
    mockUseEpisodesByMode.mockImplementation(() => ({
      data: { episodes: [] },
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    }))

    renderMap()

    await waitFor(() => {
      expect(
        screen.getByText(/No pudimos obtener los datos/i),
      ).toBeInTheDocument()
    })

    // The empty state message should NOT appear alongside the error
    expect(
      screen.queryByText(/No hay incendios activos ni recientes/i),
    ).not.toBeInTheDocument()
  })

  it('shows retry button that calls refetch', async () => {
    const user = userEvent.setup()
    const refetchActive = vi.fn()
    const refetchRecent = vi.fn()

    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: mode === 'active' ? refetchActive : refetchRecent,
    }))

    renderMap()

    const retryButton = await screen.findByText('Reintentar')
    await user.click(retryButton)

    expect(refetchActive).toHaveBeenCalled()
    expect(refetchRecent).toHaveBeenCalled()
  })

  it('renders map even when queries error', async () => {
    mockUseEpisodesByMode.mockImplementation(() => ({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    }))

    renderMap()

    expect(await screen.findByTestId('fire-map')).toBeInTheDocument()
  })
})
