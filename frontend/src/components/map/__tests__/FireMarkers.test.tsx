import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/context/LanguageContext'
import { FireMarkers } from '../layers/FireMarkers'
import type { FireMapItem } from '@/types/map'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('leaflet', () => ({
  __esModule: true,
  default: {
    divIcon: vi.fn(() => ({})),
  },
}))

vi.mock('react-leaflet', () => ({
  Marker: ({
    children,
    eventHandlers,
  }: {
    children: React.ReactNode
    eventHandlers?: { click?: () => void }
  }) => (
    <div data-testid="marker" onClick={() => eventHandlers?.click?.()}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popup">{children}</div>
  ),
}))

describe('FireMarkers', () => {
  const fire: FireMapItem = {
    id: 'fire-123',
    representative_event_id: 'event-123',
    title: 'Test Fire',
    lat: -34.6,
    lon: -58.38,
    severity: 'high',
    province: 'Cordoba',
    hectares: 1200,
    in_protected_area: true,
    overlap_percentage: 12.3,
    protected_area_name: 'Reserva',
    count_protected_areas: 2,
  }

  beforeEach(() => {
    mockNavigate.mockClear()
    sessionStorage.clear()
  })

  it('renders popup with detail button and protected info', () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <FireMarkers fires={[fire]} />
        </I18nProvider>
      </MemoryRouter>
    )

    expect(screen.getByText('Ver detalles')).toBeInTheDocument()
    expect(screen.getByText('Test Fire')).toBeInTheDocument()
    expect(screen.getByText(/12.3%/)).toBeInTheDocument()
    expect(screen.getByText(/Reserva/)).toBeInTheDocument()
  })

  it('navigates to fire detail with map return context on click', () => {
    render(
      <MemoryRouter>
        <I18nProvider>
          <FireMarkers fires={[fire]} />
        </I18nProvider>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByText('Ver detalles'))

    expect(mockNavigate).toHaveBeenCalledWith(`/fires/${fire.representative_event_id}`, {
      state: { returnTo: 'map', map: { selectedFireId: fire.id } },
    })
    // Should also persist to sessionStorage
    const stored = JSON.parse(sessionStorage.getItem('fg:return_context')!)
    expect(stored.returnTo).toBe('map')
    expect(stored.map.selectedFireId).toBe('fire-123')
  })

  it('falls back to fire id when representative_event_id is missing', () => {
    const fireNoRep: FireMapItem = {
      ...fire,
      representative_event_id: null,
    }

    render(
      <MemoryRouter>
        <I18nProvider>
          <FireMarkers fires={[fireNoRep]} />
        </I18nProvider>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByText('Ver detalles'))
    expect(mockNavigate).toHaveBeenCalledWith(`/fires/${fireNoRep.id}`, expect.any(Object))
  })

  it('fires onFireSelect when marker is clicked', () => {
    const onFireSelect = vi.fn()

    render(
      <MemoryRouter>
        <I18nProvider>
          <FireMarkers fires={[fire]} onFireSelect={onFireSelect} />
        </I18nProvider>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('marker'))
    expect(onFireSelect).toHaveBeenCalledWith(expect.objectContaining({ id: fire.id }))
  })

  it('renders fire_detail popup variant without detail button', () => {
    const fireDetail: FireMapItem = {
      ...fire,
      status: 'monitoring',
      in_protected_area: false,
      overlap_percentage: null,
      protected_area_name: null,
      count_protected_areas: null,
    }

    render(
      <MemoryRouter>
        <I18nProvider>
          <FireMarkers fires={[fireDetail]} popupVariant="fire_detail" />
        </I18nProvider>
      </MemoryRouter>
    )

    expect(screen.getByText('Incendio en monitoreo')).toBeInTheDocument()
    expect(screen.queryByText('Ver detalles')).not.toBeInTheDocument()
    expect(screen.getByText(/Áreas protegidas:/)).toBeInTheDocument()
    expect(screen.getByText(/Áreas protegidas: N\/A/)).toBeInTheDocument()
  })
})

