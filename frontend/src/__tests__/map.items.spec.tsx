import { render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import MapPage from '@/pages/MapPage'

const mockUseEpisodesByMode = vi.fn()
const fireMapSpy = vi.fn()

vi.mock('@/hooks/queries/useEpisodesByMode', () => ({
  useEpisodesByMode: (mode: string) => mockUseEpisodesByMode(mode),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: (props: { fires: unknown[] }) => {
    fireMapSpy(props)
    return <div data-testid="fire-map" />
  },
}))

const renderMap = () =>
  render(
    <I18nProvider>
      <MapPage />
    </I18nProvider>,
  )

describe('MapPage items mapping', () => {
  it('maps centroid and representative_event_id', async () => {
    const episode = {
      id: 'episode-1',
      centroid_lat: 10.5,
      centroid_lon: -64.3,
      frp_max: 55,
      status: 'active',
      provinces: ['Chubut'],
      estimated_area_hectares: 123,
      representative_event_id: 'event-999',
    }

    mockUseEpisodesByMode.mockImplementation((mode: string) => ({
      data: { episodes: mode === 'active' ? [episode] : [] },
      isLoading: false,
    }))

    renderMap()

    await waitFor(() => {
      expect(fireMapSpy).toHaveBeenCalled()
    })

    const props = fireMapSpy.mock.calls[0][0]
    expect(props.fires).toHaveLength(1)
    expect(props.fires[0].lat).toBe(10.5)
    expect(props.fires[0].lon).toBe(-64.3)
    expect(props.fires[0].representative_event_id).toBe('event-999')
  })
})
