import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapContainer } from 'react-leaflet'
import { FireMarkers } from '../FireMarkers'
import type { FireMapItem } from '@/types/map'

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

const baseFire: FireMapItem = {
  id: 'fire-1',
  title: 'Incendio en Córdoba',
  lat: -31.4,
  lon: -64.2,
  severity: 'high',
  province: 'Córdoba',
  status: 'active',
  hectares: 150,
  in_protected_area: false,
  overlap_percentage: null,
  protected_area_name: null,
  count_protected_areas: null,
}

function renderWithMap(ui: React.ReactElement) {
  return render(
    <MapContainer center={[-34, -64]} zoom={5} style={{ height: 400, width: 600 }}>
      {ui}
    </MapContainer>,
  )
}

describe('FireMarkers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing when fires array is empty', () => {
    const { container } = renderWithMap(
      <FireMarkers fires={[]} />,
    )
    expect(container.querySelector('.leaflet-marker-icon')).toBeNull()
  })

  it('renders markers for each fire', () => {
    const fires: FireMapItem[] = [
      baseFire,
      { ...baseFire, id: 'fire-2', lat: -32, lon: -65, severity: 'low' },
    ]
    const { container } = renderWithMap(
      <FireMarkers fires={fires} />,
    )
    const markers = container.querySelectorAll('.custom-fire-marker')
    expect(markers.length).toBe(2)
  })

  it('applies fire-popup className to popups', () => {
    const { container } = renderWithMap(
      <FireMarkers fires={[baseFire]} selectedFireId="fire-1" />,
    )
    // Wait for popup to open via selectedFireId
    const popup = container.querySelector('.fire-popup')
    expect(popup).toBeTruthy()
  })

  it('renders viewDetails CTA button in default variant', () => {
    renderWithMap(
      <FireMarkers fires={[baseFire]} selectedFireId="fire-1" popupVariant="default" />,
    )
    expect(screen.getByText('viewDetails')).toBeInTheDocument()
  })

  it('renders status title in fire_detail variant', () => {
    renderWithMap(
      <FireMarkers
        fires={[baseFire]}
        selectedFireId="fire-1"
        popupVariant="fire_detail"
      />,
    )
    expect(screen.getByText('firePopupTitleActive')).toBeInTheDocument()
  })

  it('renders severity badge in fire_detail variant', () => {
    renderWithMap(
      <FireMarkers
        fires={[baseFire]}
        selectedFireId="fire-1"
        popupVariant="fire_detail"
      />,
    )
    expect(screen.getByText('severityHigh')).toBeInTheDocument()
  })

  it('renders compact popup dimensions for fire_detail variant', () => {
    const { container } = renderWithMap(
      <FireMarkers
        fires={[baseFire]}
        selectedFireId="fire-1"
        popupVariant="fire_detail"
      />,
    )
    const popupContent = container.querySelector('.fire-popup .leaflet-popup-content')
    const innerDiv = popupContent?.querySelector('div')
    expect(innerDiv?.className).toContain('max-w-[260px]')
    expect(innerDiv?.className).toContain('min-w-[180px]')
  })

  it('does not render viewDetails button in fire_detail variant', () => {
    renderWithMap(
      <FireMarkers
        fires={[baseFire]}
        selectedFireId="fire-1"
        popupVariant="fire_detail"
      />,
    )
    expect(screen.queryByText('viewDetails')).not.toBeInTheDocument()
  })
})
