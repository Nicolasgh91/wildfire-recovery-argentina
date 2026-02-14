import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/context/LanguageContext'
import MapPage from '@/pages/MapPage'

const mockUseEpisodesByMode = vi.fn()

vi.mock('@/hooks/queries/useEpisodesByMode', () => ({
  useEpisodesByMode: (mode: string) => mockUseEpisodesByMode(mode),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="fire-map" />,
}))

describe('MapPage', () => {
  it('renders the map layout with fire list content', async () => {
    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: {
        episodes:
          mode === 'active'
            ? [
              {
                id: 'episode-1',
                centroid_lat: 10,
                centroid_lon: -64,
                frp_max: 25,
                status: 'active',
                provinces: ['Chubut'],
                estimated_area_hectares: 120,
                representative_event_id: 'event-1',
              },
            ]
            : [],
      },
      isLoading: false,
    }))

    render(
      <MemoryRouter>
        <I18nProvider>
          <MapPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText('Mapa Interactivo')).toBeInTheDocument()
    expect(await screen.findByTestId('fire-map')).toBeInTheDocument()

    const provinceMatches = screen.getAllByText('Chubut')
    expect(provinceMatches.length).toBeGreaterThan(0)
  })
})
