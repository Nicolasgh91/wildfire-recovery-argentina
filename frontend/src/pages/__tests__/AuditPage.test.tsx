<<<<<<< HEAD
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuditPage from '@/pages/Audit'
import { RETURN_CONTEXT_KEY, type ReturnContext, type AuditReturnContext } from '@/types/navigation'

vi.mock('@/components/audit-map', () => ({
  AuditMap: () => <div data-testid="mock-audit-map" />,
}))

vi.mock('@/context/LanguageContext', () => ({
=======
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuditPage from '../Audit'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'

jest.mock('@/context/LanguageContext', () => ({
>>>>>>> 78c42e55cef136337181fe8c6511a8d52e9838ab
  useI18n: () => ({
    t: (key: string) => key,
    language: 'es',
  }),
}))

<<<<<<< HEAD
const mockUseAuth = vi.fn(() => ({ isAuthenticated: true, status: 'authenticated' as const }))
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

const mockNavigate = vi.fn()
let mockLocationState: { restore?: AuditReturnContext } | undefined

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      pathname: '/audit',
      search: '',
      hash: '',
      state: mockLocationState,
      key: 'test',
    }),
  }
})

const mockSearchAuditEpisodes = vi.fn()
vi.mock('@/services/endpoints/audit-search', () => ({
  searchAuditEpisodes: (...args: unknown[]) => mockSearchAuditEpisodes(...args),
}))

const mockUseAuditMutation = vi.fn()
vi.mock('@/hooks/mutations/useAudit', () => ({
  useAuditMutation: () => mockUseAuditMutation(),
}))

function renderWithRouter(ui: ReactNode, initialState?: ReturnContext) {
  return render(
    <MemoryRouter
      initialEntries={[
        {
          pathname: '/audit',
          state: initialState,
        },
      ]}
    >
      <Routes>
        <Route path="/audit" element={ui} />
        <Route path="/fires/:id" element={<div data-testid="fire-detail-page" />} />
        <Route path="/login" element={<div data-testid="login-page" />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuditPage navigation and sessionStorage', () => {
  beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    sessionStorage.clear()
    mockNavigate.mockReset()
    mockLocationState = undefined
    mockSearchAuditEpisodes.mockReset()
    mockUseAuditMutation.mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: vi.fn(),
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('D-09/D-10: clicking result.fires link navigates with ReturnContext.audit (land-use) and stores minimal data in sessionStorage', () => {
    const fireId = 'fire-event-1234'
    const ctx: ReturnContext = {
      returnTo: 'audit',
      audit: {
        origin: 'land-use',
        lat: -31.4,
        lon: -64.2,
        radius_m: 1000,
        page: 1,
      },
    }

    mockLocationState = { restore: ctx.audit as AuditReturnContext }

    mockUseAuditMutation.mockReturnValue({
      data: {
        is_prohibited: true,
        fires_found: 1,
        fires: [
          {
            fire_event_id: fireId,
            fire_date: '2024-01-01',
            distance_meters: 250,
            in_protected_area: false,
            prohibition_until: '2025-01-01',
            years_remaining: 1,
            province: 'Córdoba',
          },
        ],
        evidence: { thumbnails: [] },
        audit_id: 'audit-1',
        audit_hash: 'hash',
        location: { lat: -31.4, lon: -64.2 },
        radius_meters: 1000,
      },
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: vi.fn(),
    })

    renderWithRouter(<AuditPage />)

    const cards = screen.getAllByRole('button', { hidden: true }).filter((btn) => btn.querySelector('svg'))
    const detailButton = cards[cards.length - 1]

    fireEvent.click(detailButton)

    expect(mockNavigate).toHaveBeenCalledTimes(1)
    const [path, options] = mockNavigate.mock.calls[0]
    expect(path).toBe(`/fires/${fireId}`)

    const state = (options as { state?: ReturnContext })?.state
    expect(state?.returnTo).toBe('audit')
    expect(state?.audit).toEqual({
      origin: 'land-use',
      lat: -31.4,
      lon: -64.2,
      radius_m: 1000,
      page: 1,
    })

    const storedRaw = sessionStorage.getItem(RETURN_CONTEXT_KEY)
    expect(storedRaw).not.toBeNull()
    const stored = JSON.parse(storedRaw as string) as ReturnContext
    expect(stored.returnTo).toBe('audit')
    expect(stored.audit).toBeDefined()
    expect(stored.audit).not.toHaveProperty('fires')
    expect(stored.audit).not.toHaveProperty('results')
  })

  it('D-14: navigation from episodes grid uses textual AuditReturnContext with { q, page } shape', async () => {
    const fireId = 'episode-fire-9999'

    mockUseAuditMutation.mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: vi.fn(),
    })

    mockSearchAuditEpisodes.mockResolvedValue({
      resolved_place: {
        label: 'Rio Tercero, Córdoba',
        type: 'address',
      },
      episodes: [
        {
          id: 'episode-1',
          fire_event_id: fireId,
          start_date: '2024-01-01',
          end_date: '2024-01-02',
          status: 'extinguished',
          provinces: ['Córdoba'],
          estimated_area_hectares: 100,
          detection_count: 10,
          frp_max: 50,
        },
      ],
      total: 1,
      date_range: {
        earliest: '2024-01-01',
        latest: '2024-01-02',
      },
    })

    renderWithRouter(<AuditPage />)

    const searchInput = screen.getByTestId('search-place')
    fireEvent.change(searchInput, { target: { value: 'Rio Tercero' } })

    const form = searchInput.closest('form')
    if (!form) {
      throw new Error('Form not found')
    }
    fireEvent.submit(form)

    await waitFor(() => expect(mockSearchAuditEpisodes).toHaveBeenCalled())

    const linkButtons = screen.getAllByRole('button', { hidden: true }).filter((btn) => btn.querySelector('svg'))
    const detailButton = linkButtons[linkButtons.length - 1]

    fireEvent.click(detailButton)

    expect(mockNavigate).toHaveBeenCalledTimes(1)
    const [path, options] = mockNavigate.mock.calls[0]
    expect(path).toBe(`/fires/${fireId}`)

    const state = (options as { state?: ReturnContext })?.state
    expect(state?.returnTo).toBe('audit')
    expect(state?.audit).toEqual({
      origin: 'search',
      q: 'Rio Tercero',
      radius_km: 1,
      page: 1,
    })

    const storedRaw = sessionStorage.getItem(RETURN_CONTEXT_KEY)
    expect(storedRaw).not.toBeNull()
    const stored = JSON.parse(storedRaw as string) as ReturnContext
    expect(stored.returnTo).toBe('audit')
    expect(stored.audit).toEqual({
      origin: 'search',
      q: 'Rio Tercero',
      radius_km: 1,
      page: 1,
    })
  })
})

describe('AuditPage UI styles (UC-F06)', () => {
  beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    sessionStorage.clear()
    mockNavigate.mockReset()
    mockLocationState = undefined
    mockSearchAuditEpisodes.mockReset()
    mockUseAuditMutation.mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: vi.fn(),
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('D-02/D-03: area presets use brown secondary variant with opacity on selected', () => {
    renderWithRouter(<AuditPage />)

    const preset500 = screen.getByRole('button', { name: 'Alrededores (500 m)' })
    const preset1000 = screen.getByRole('button', { name: 'Zona (1 km)' })
    const preset3000 = screen.getByRole('button', { name: 'Amplio (3 km)' })

    // analysisPreset default es 1000 => \"Zona (1 km)\" seleccionado con opacidad 0.6
    expect(preset1000.className).toContain('opacity-60')

    // Los presets no seleccionados no deben tener opacidad reducida
    expect(preset500.className).not.toContain('opacity-60')
    expect(preset3000.className).not.toContain('opacity-60')
  })

  it('D-04/D-05/D-06: pagination buttons toggle disabled state correctly', async () => {
    const episodes = Array.from({ length: 15 }).map((_, idx) => ({
      id: `episode-${idx + 1}`,
      fire_event_id: `fire-${idx + 1}`,
      start_date: '2024-01-01',
      end_date: '2024-01-02',
      status: 'extinguished',
      provinces: ['Córdoba'],
      estimated_area_hectares: 100,
      detection_count: 10,
      frp_max: 50,
    }))

    mockSearchAuditEpisodes.mockResolvedValue({
      resolved_place: {
        label: 'Rio Tercero, Córdoba',
        type: 'address',
      },
      episodes,
      total: episodes.length,
      date_range: {
        earliest: '2024-01-01',
        latest: '2024-01-02',
      },
    })

    renderWithRouter(<AuditPage />)

    const searchInput = screen.getByTestId('search-place')
    fireEvent.change(searchInput, { target: { value: 'Rio Tercero' } })

    const form = searchInput.closest('form')
    if (!form) throw new Error('Form not found')
    fireEvent.submit(form)

    await waitFor(() => expect(mockSearchAuditEpisodes).toHaveBeenCalled())

    const prevButton = screen.getByRole('button', { name: /Anterior/ })
    const nextButton = screen.getByRole('button', { name: /Siguiente/ })

    // Primera página: \"Anterior\" deshabilitado, \"Siguiente\" habilitado
    expect(prevButton).toBeDisabled()
    expect(nextButton).not.toBeDisabled()

    // Ir a página intermedia (página 2 de 2)
    fireEvent.click(nextButton)

    expect(prevButton).not.toBeDisabled()
    expect(nextButton).toBeDisabled()
  })
})


=======
jest.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    status: 'authenticated',
  }),
}))

jest.mock('@/hooks/mutations/useAudit', () => ({
  useAuditMutation: () => ({
    reset: jest.fn(),
    mutate: jest.fn(),
    data: {
      is_prohibited: false,
      fires_found: 1,
      fires: [
        {
          fire_event_id: 'abc123456789',
          fire_date: '2024-01-01T00:00:00Z',
          province: 'Provincia',
          distance_meters: 1000,
          prohibition_until: null,
          in_protected_area: false,
          protected_area_names: [],
        },
      ],
      evidence: { thumbnails: [] },
    },
    isPending: false,
    error: null,
  }),
}))

jest.mock('@/services/endpoints/audit-search', () => ({
  searchAuditEpisodes: jest.fn().mockResolvedValue({
    total: 1,
    resolved_place: { label: 'Lugar', type: 'province' },
    date_range: { earliest: '2024-01-01', latest: '2024-01-02' },
    episodes: [
      {
        id: 'episode-1',
        start_date: '2024-01-01',
        end_date: '2024-01-02',
        status: 'extinct',
        provinces: ['Provincia'],
        frp_max: 10,
        estimated_area_hectares: 100,
        detection_count: 5,
      },
    ],
  }),
}))

jest.mock('@/services/endpoints/geocode', () => ({
  reverseGeocode: jest.fn(),
}))

jest.mock('lucide-react', () => {
  const original = jest.requireActual('lucide-react')
  return {
    ...original,
    Loader2: (props: any) => <svg data-testid="loader2" {...props} />,
  }
})

const renderWithRouter = () =>
  render(
    <MemoryRouter initialEntries={['/audit']}>
      <Routes>
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/fires/:id" element={<div>Fire Detail</div>} />
      </Routes>
    </MemoryRouter>,
  )

describe('AuditPage UI and navigation', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('applies a stronger secondary background only to the selected preset', () => {
    renderWithRouter()

    const buttons = screen.getAllByRole('button').filter((btn) =>
      btn.textContent?.includes('Alrededores') ||
      btn.textContent?.includes('Zona') ||
      btn.textContent?.includes('Amplio'),
    )

    const selected = buttons.find((btn) => btn.className.includes('bg-secondary/90'))
    const unselected = buttons.filter((btn) => btn !== selected)

    expect(selected).toBeDefined()
    expect(selected?.className).toContain('bg-secondary/90')

    unselected.forEach((btn) => {
      expect(btn.className).not.toContain('bg-secondary/90')
    })
  })

  it('keeps pagination buttons brown and only toggles disabled state', async () => {
    renderWithRouter()

    const input = screen.getByTestId('search-place') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Buenos Aires' } })

    const submit = screen.getByTestId('audit-submit')
    fireEvent.click(submit)

    const prevButton = await screen.findByRole('button', { name: /Anterior/i })
    const nextButton = screen.getByRole('button', { name: /Siguiente/i })

    expect(prevButton).toBeDisabled()
    expect(prevButton.className).not.toContain('bg-secondary/90')

    expect(nextButton).not.toBeDisabled()
    expect(nextButton.className).not.toContain('bg-secondary/90')
  })

  it('shows truncated fire_event_id with tooltip and stores minimal AuditReturnContext in sessionStorage on navigation', async () => {
    renderWithRouter()

    const detailButton = await screen.findByRole('button', { name: /seeDetail|Ver detalle/i })
    fireEvent.click(detailButton)

    expect(screen.getByText('Fire Detail')).toBeInTheDocument()

    const stored = sessionStorage.getItem(RETURN_CONTEXT_KEY)
    expect(stored).not.toBeNull()

    const parsed = JSON.parse(stored!)
    expect(parsed.returnTo).toBe('audit')
    expect(parsed.audit).toEqual(
      expect.objectContaining({
        lat: expect.any(Number),
        lon: expect.any(Number),
        radius: expect.any(Number),
        page: expect.any(Number),
      }),
    )
    const keys = Object.keys(parsed.audit)
    expect(keys.sort()).toEqual(['lat', 'lon', 'page', 'radius'].sort())
  })
})

>>>>>>> 78c42e55cef136337181fe8c6511a8d52e9838ab
