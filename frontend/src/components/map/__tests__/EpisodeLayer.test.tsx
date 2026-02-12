import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { latLngToCell } from 'h3-js'
import { I18nProvider } from '@/context/LanguageContext'
import { EpisodeLayer } from '../layers/EpisodeLayer'
import { getEpisodeStyle } from '@/lib/leaflet/styles'

let latestProps: any

vi.mock('react-leaflet', () => ({
  GeoJSON: (props: any) => {
    latestProps = props
    return <div data-testid="geojson" />
  },
}))

describe('EpisodeLayer', () => {
  const episode = {
    id: 'episode-1',
    representative_event_id: 'event-1',
    title: 'Episode Title',
    h3_index: latLngToCell(-34.6037, -58.3816, 5),
    severity: 'high' as const,
    status: 'active' as const,
    province: 'Cordoba',
    hectares: 900,
    in_protected_area: true,
    overlap_percentage: 10.5,
    protected_area_name: 'Reserva',
    count_protected_areas: 1,
  }

  it('binds popup and handles events', () => {
    const onEpisodeClick = vi.fn()

    render(
      <I18nProvider>
        <EpisodeLayer episodes={[episode]} onEpisodeClick={onEpisodeClick} />
      </I18nProvider>
    )

    const feature = {
      type: 'Feature',
      properties: episode,
      geometry: {
        type: 'Polygon',
        coordinates: [],
      },
    }

    const bindPopup = vi.fn()
    let handlers: any = null
    const layer = {
      bindPopup,
      on: (events: any) => {
        handlers = events
      },
    }

    latestProps.onEachFeature(feature, layer)

    expect(bindPopup).toHaveBeenCalledWith(
      expect.stringContaining(`/fires/${encodeURIComponent(episode.representative_event_id)}`)
    )

    handlers.click()
    expect(onEpisodeClick).toHaveBeenCalledWith(expect.objectContaining({ id: episode.id }))

    const target = { setStyle: vi.fn() }
    handlers.mouseover({ target })
    expect(target.setStyle).toHaveBeenCalledWith(expect.objectContaining({ weight: 3 }))

    handlers.mouseout({ target })
    expect(target.setStyle).toHaveBeenCalledWith(getEpisodeStyle(episode))
  })

  it('falls back to episode id when representative_event_id is missing', () => {
    const episodeNoRep = {
      ...episode,
      representative_event_id: null,
    }

    render(
      <I18nProvider>
        <EpisodeLayer episodes={[episodeNoRep]} />
      </I18nProvider>
    )

    const feature = {
      type: 'Feature',
      properties: episodeNoRep,
      geometry: {
        type: 'Polygon',
        coordinates: [],
      },
    }

    const bindPopup = vi.fn()
    const layer = {
      bindPopup,
      on: vi.fn(),
    }

    latestProps.onEachFeature(feature, layer)

    expect(bindPopup).toHaveBeenCalledWith(
      expect.stringContaining(`/fires/${encodeURIComponent(episodeNoRep.id)}`)
    )
  })
})
