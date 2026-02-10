import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MapView } from '../MapView'

vi.mock('react-leaflet', () => ({
  useMap: () => ({ setView: vi.fn(), getZoom: () => 5 }),
}))

vi.mock('../BaseMap', () => ({
  BaseMap: ({
    children,
    tileLayer,
    interactive,
  }: {
    children: React.ReactNode
    tileLayer?: string
    interactive?: boolean
  }) => (
    <div
      data-testid="base-map"
      data-tile-layer={tileLayer}
      data-interactive={String(interactive)}
    >
      {children}
    </div>
  ),
}))

vi.mock('../layers/FireMarkers', () => ({
  FireMarkers: () => <div data-testid="fire-markers" />,
}))

vi.mock('../layers/EpisodeLayer', () => ({
  EpisodeLayer: () => <div data-testid="episode-layer" />,
}))

vi.mock('../layers/H3HeatmapLayer', () => ({
  H3HeatmapLayer: () => <div data-testid="heatmap-layer" />,
}))

vi.mock('../layers/ProtectedAreas', () => ({
  ProtectedAreas: () => <div data-testid="protected-areas" />,
}))

describe('MapView', () => {
  it('renders base map and core layers', () => {
    render(<MapView tileLayer="satellite" />)

    const base = screen.getByTestId('base-map')
    expect(base).toHaveAttribute('data-tile-layer', 'satellite')
    expect(screen.getByTestId('fire-markers')).toBeInTheDocument()
    expect(screen.getByTestId('episode-layer')).toBeInTheDocument()
  })

  it('renders optional layers when enabled', () => {
    render(<MapView showHeatmap showProtectedAreas />)

    expect(screen.getByTestId('heatmap-layer')).toBeInTheDocument()
    expect(screen.getByTestId('protected-areas')).toBeInTheDocument()
  })
})
