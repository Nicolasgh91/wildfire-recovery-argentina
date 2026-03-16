import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FireDetailPage from '@/pages/FireDetail'
import { RETURN_CONTEXT_KEY, type ReturnContext } from '@/types/navigation'
import { HOME_PATH } from '@/lib/routing'

vi.mock('@/hooks/queries/useFire', () => ({
  useFire: () => ({
    data: {
      source_type: 'event',
      fire: {
        id: 'fire-1',
        start_date: '2024-01-01',
        end_date: '2024-01-02',
        status: 'extinguished',
        department: 'Depto',
        province: 'Provincia',
        estimated_area_hectares: 100,
        total_detections: 10,
        in_protected_area: false,
        overlap_percentage: null,
        protected_areas: [],
        avg_confidence: 80,
        max_frp: 50,
        centroid: { latitude: -31.4, longitude: -64.2 },
        count_protected_areas: 0,
      },
    },
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/hooks/queries/useFireQuality', () => ({
  useFireQuality: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="mock-fire-map" />,
}))

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: false }),
}))

function renderWithRouter(
  ui: ReactNode,
  {
    route = '/fires/fire-1',
    initialEntries = ['/fires/fire-1'],
    state,
  }: { route?: string; initialEntries?: string[]; state?: ReturnContext } = {},
) {
  const queryClient = new QueryClient()

  return render(
    <MemoryRouter initialEntries={[{ pathname: route, state }]}>
      <Routes>
        <Route
          path="/fires/:id"
          element={
            <QueryClientProvider client={queryClient}>
              {ui}
            </QueryClientProvider>
          }
        />
        <Route path={HOME_PATH} element={<div data-testid="home-page" />} />
        <Route path="/fires/history" element={<div data-testid="history-page" />} />
        <Route path="/map" element={<div data-testid="map-page" />} />
        <Route path="/audit" element={<div data-testid="audit-page" />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('FireDetailPage navigation back button', () => {
  beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    sessionStorage.clear()
  })

  it('navigates back to home when context returnTo=home', () => {
    const ctx: ReturnContext = { returnTo: 'home', home: { scrollY: 100 } }
    renderWithRouter(<FireDetailPage />, { state: ctx })

    const backButton = screen.getByText('goBack')
    fireEvent.click(backButton)

    expect(screen.getByTestId('home-page')).toBeInTheDocument()
  })

  it('navigates back to history when context returnTo=history', () => {
    const ctx: ReturnContext = { returnTo: 'history', history: { search: '?page=2' } }
    renderWithRouter(<FireDetailPage />, { state: ctx })

    const backButton = screen.getByText('goBack')
    fireEvent.click(backButton)

    expect(screen.getByTestId('history-page')).toBeInTheDocument()
  })

  it('navigates back to map when context returnTo=map', () => {
    const ctx: ReturnContext = { returnTo: 'map', map: { selectedFireId: 'fire-1' } }
    renderWithRouter(<FireDetailPage />, { state: ctx })

    const backButton = screen.getByText('goBack')
    fireEvent.click(backButton)

    expect(screen.getByTestId('map-page')).toBeInTheDocument()
  })

  it('hides back button when there is no ReturnContext', () => {
    renderWithRouter(<FireDetailPage />)
    expect(screen.queryByText('goBack')).not.toBeInTheDocument()
  })

  it('uses sessionStorage context when state is empty', () => {
    const ctx: ReturnContext = { returnTo: 'history', history: { search: '?page=3' } }
    sessionStorage.setItem(RETURN_CONTEXT_KEY, JSON.stringify(ctx))

    renderWithRouter(<FireDetailPage />)
    const backButton = screen.getByText('goBack')
    fireEvent.click(backButton)

    expect(screen.getByTestId('history-page')).toBeInTheDocument()
    expect(sessionStorage.getItem(RETURN_CONTEXT_KEY)).toBeNull()
  })

  it('navigates back to audit when context returnTo=audit', () => {
    const ctx: ReturnContext = {
      returnTo: 'audit',
      audit: {
        origin: 'search',
        q: 'Rio Tercero',
        radius_km: 1,
        page: 2,
      },
    }

    renderWithRouter(<FireDetailPage />, { state: ctx })

    const backButton = screen.getByText('goBack')
    fireEvent.click(backButton)

    expect(screen.getByTestId('audit-page')).toBeInTheDocument()
  })
})

