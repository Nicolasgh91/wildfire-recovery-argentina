import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeAll, vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import FireDetailPage from '@/pages/FireDetail'

// Track navigate calls
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

beforeAll(() => {
  if (!globalThis.ResizeObserver) {
    globalThis.ResizeObserver = class {
      observe() { }
      unobserve() { }
      disconnect() { }
    }
  }
})

vi.mock('@/hooks/queries/useFire', () => ({
  useFire: () => ({
    data: {
      fire: {
        id: 'fire-123',
        start_date: '2026-02-01T00:00:00Z',
        end_date: '2026-02-02T00:00:00Z',
        duration_hours: 24,
        centroid: { latitude: -31.4, longitude: -64.2 },
        province: 'Cordoba',
        department: 'Capital',
        total_detections: 12,
        avg_confidence: 78.5,
        max_frp: 55,
        estimated_area_hectares: 1200,
        is_significant: true,
        has_satellite_imagery: true,
        has_climate_data: true,
        in_protected_area: true,
        overlap_percentage: 12.5,
        count_protected_areas: 1,
        status: 'active',
        slides_data: [
          {
            type: 'true_color',
            title: 'Imagen 1',
            url: 'https://example.com/slide.jpg',
          },
        ],
        protected_areas: [
          {
            id: 'area-1',
            name: 'Parque Nacional',
            category: 'Parque',
          },
        ],
        created_at: '2026-02-01T00:00:00Z',
        updated_at: '2026-02-02T00:00:00Z',
      },
      detections: [],
      related_fires_count: 2,
    },
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/queries/useFireQuality', () => ({
  useFireQuality: () => ({
    data: {
      fire_event_id: 'fire-123',
      start_date: '2026-02-01T00:00:00Z',
      province: 'Cordoba',
      metrics: {
        reliability_score: 85,
        classification: 'high',
        confidence_score: 80,
        imagery_score: 100,
        climate_score: 90,
        independent_score: 50,
        avg_confidence: 78.5,
        total_detections: 12,
        independent_sources: 2,
        has_imagery: true,
        has_climate: true,
        has_ndvi: false,
        score_calculated_at: '2026-02-02T00:00:00Z',
      },
      limitations: [],
      sources: [],
      warnings: [],
    },
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="fire-map" />,
}))

function renderDetail(initialState?: Record<string, unknown>) {
  return render(
    <I18nProvider>
      <MemoryRouter
        initialEntries={[{ pathname: '/fires/fire-123', state: initialState }]}
      >
        <Routes>
          <Route path="/fires/:id" element={<FireDetailPage />} />
        </Routes>
      </MemoryRouter>
    </I18nProvider>,
  )
}

describe('FireDetailPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    sessionStorage.clear()
  })

  it('renders fire detail with quality indicator and carousel', () => {
    renderDetail()

    expect(screen.getByText('Provincia')).toBeInTheDocument()
    expect(screen.getByText('Cordoba')).toBeInTheDocument()
    expect(screen.getByText('Calidad de datos')).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('renders back button with "Volver atrás" text', () => {
    renderDetail()

    expect(screen.getByText('Volver atrás')).toBeInTheDocument()
    expect(screen.queryByText('Históricos')).not.toBeInTheDocument()
  })

  it('navigates to Home with restore state when returnTo is home', () => {
    renderDetail({ returnTo: 'home', home: { scrollY: 500 } })

    fireEvent.click(screen.getByText('Volver atrás'))

    expect(mockNavigate).toHaveBeenCalledWith('/', {
      state: { restore: { scrollY: 500 } },
    })
  })

  it('navigates to Map with restore state when returnTo is map', () => {
    renderDetail({ returnTo: 'map', map: { selectedFireId: 'fire-abc' } })

    fireEvent.click(screen.getByText('Volver atrás'))

    expect(mockNavigate).toHaveBeenCalledWith('/map', {
      state: { restore: { selectedFireId: 'fire-abc' } },
    })
  })

  it('navigates to Map even without selectedFireId', () => {
    renderDetail({ returnTo: 'map' })

    fireEvent.click(screen.getByText('Volver atrás'))

    expect(mockNavigate).toHaveBeenCalledWith('/map', {
      state: { restore: { selectedFireId: undefined } },
    })
  })

  it('falls back to Home when no state is provided', () => {
    renderDetail()

    fireEvent.click(screen.getByText('Volver atrás'))

    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('falls back to sessionStorage when location.state is missing', () => {
    const ctx = { returnTo: 'home', home: { scrollY: 300 } }
    sessionStorage.setItem('fg:return_context', JSON.stringify(ctx))

    renderDetail()

    fireEvent.click(screen.getByText('Volver atrás'))

    expect(mockNavigate).toHaveBeenCalledWith('/', {
      state: { restore: { scrollY: 300 } },
    })
    // Should clean up sessionStorage after use
    expect(sessionStorage.getItem('fg:return_context')).toBeNull()
  })
})
