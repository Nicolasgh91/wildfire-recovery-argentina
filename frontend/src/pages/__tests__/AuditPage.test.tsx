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
  useI18n: () => ({
    t: (key: string) => key,
    language: 'es',
  }),
}))

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
    vi.spyOn(window.history, 'replaceState')
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

  it('D-09/D-10: clicking result.fires link navigates with ReturnContext.audit (land-use) and stores minimal data in sessionStorage', async () => {
    const fireId = 'fire-event-1234'

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

    // Set lat/lon values in the form so handleFireDetailNavFromPoint has valid coordinates
    const accordion = screen.getByText('advancedOptions')
    fireEvent.click(accordion)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('-38.4161')).toBeInTheDocument()
    })

    const latInput = screen.getByPlaceholderText('-38.4161')
    const lonInput = screen.getByPlaceholderText('-63.6167')
    fireEvent.change(latInput, { target: { value: '-31.4' } })
    fireEvent.change(lonInput, { target: { value: '-64.2' } })

    // Find the ExternalLink button (last SVG button in result.fires section)
    const allButtons = screen.getAllByRole('button', { hidden: true }).filter((btn) => btn.querySelector('svg'))
    const detailButton = allButtons[allButtons.length - 1]

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

  it('B2-04: restores from search origin exactly once even if history state persists', async () => {
    const fireId = 'episode-fire-restore'

    mockUseAuditMutation.mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: vi.fn(),
    })

    mockLocationState = {
      restore: {
        origin: 'search',
        q: 'Cordoba',
        radius_km: 2,
        page: 1,
      },
    }

    mockSearchAuditEpisodes.mockResolvedValue({
      resolved_place: {
        label: 'Cordoba, Argentina',
        type: 'address',
      },
      episodes: [
        {
          id: 'episode-restore',
          fire_event_id: fireId,
          start_date: '2024-01-01',
          end_date: '2024-01-02',
          status: 'extinguished',
          provinces: ['Córdoba'],
          estimated_area_hectares: 50,
          detection_count: 5,
          frp_max: 20,
        },
      ],
      total: 1,
      date_range: {
        earliest: '2024-01-01',
        latest: '2024-01-02',
      },
    })

    // Mock replaceState to NO-OP so history.state would conceptualmente persist.
    const replaceSpy = vi
      .spyOn(window.history, 'replaceState')
      .mockImplementation(() => {})

    renderWithRouter(<AuditPage />)

    await waitFor(() => {
      expect(mockSearchAuditEpisodes).toHaveBeenCalledTimes(1)
    })

    // Even if state conceptualmente persiste, the effect must have guarded execution.
    expect(mockSearchAuditEpisodes).toHaveBeenCalledTimes(1)
    expect(replaceSpy).toHaveBeenCalledTimes(1)

    replaceSpy.mockRestore()
  })

  it('B2-04: restores from land-use origin exactly once even if history state persists', async () => {
    const mutateSpy = vi.fn()

    mockUseAuditMutation.mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      reset: vi.fn(),
      mutate: mutateSpy,
    })

    mockLocationState = {
      restore: {
        origin: 'land-use',
        lat: -31.4,
        lon: -64.2,
        radius_m: 1000,
        page: 2,
      },
    }

    const replaceSpy = vi
      .spyOn(window.history, 'replaceState')
      .mockImplementation(() => {})

    renderWithRouter(<AuditPage />)

    await waitFor(() => {
      expect(mutateSpy).toHaveBeenCalledTimes(1)
    })

    expect(mutateSpy).toHaveBeenCalledTimes(1)
    expect(replaceSpy).toHaveBeenCalledTimes(1)

    replaceSpy.mockRestore()
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

  it('D-02/D-03: non-selected presets have emerald outline classes, selected does not', () => {
    renderWithRouter(<AuditPage />)

    const preset500 = screen.getByRole('button', { name: 'Alrededores (500 m)' })
    const preset1000 = screen.getByRole('button', { name: 'Zona (1 km)' })
    const preset3000 = screen.getByRole('button', { name: 'Amplio (3 km)' })

    // D-02: non-selected presets have emerald border and text classes
    expect(preset500.className).toContain('border-emerald-600')
    expect(preset500.className).toContain('text-emerald-700')
    expect(preset3000.className).toContain('border-emerald-600')
    expect(preset3000.className).toContain('text-emerald-700')

    // D-03: selected preset (1000 default) does NOT have emerald outline classes
    expect(preset1000.className).not.toContain('border-emerald-600')
    expect(preset1000.className).not.toContain('text-emerald-700')
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

  it('D-07: result.fires shows truncated fire_event_id with title of full ID', () => {
    const fireId = 'abcdef12-3456-7890-abcd-ef1234567890'

    mockUseAuditMutation.mockReturnValue({
      data: {
        is_prohibited: false,
        fires_found: 1,
        fires: [
          {
            fire_event_id: fireId,
            fire_date: '2024-06-15',
            distance_meters: 500,
            in_protected_area: false,
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

    // Verify truncated ID visible (first 8 chars)
    const truncated = `${fireId.slice(0, 8)}...`
    expect(screen.getAllByText(truncated).length).toBeGreaterThanOrEqual(1)

    // Verify full ID is accessible via title attribute
    const idSpan = screen.getAllByTitle(fireId)
    expect(idSpan.length).toBeGreaterThanOrEqual(1)
  })

  it('D-08: result.fires without fire_event_id shows N/D and no detail link', () => {
    mockUseAuditMutation.mockReturnValue({
      data: {
        is_prohibited: false,
        fires_found: 1,
        fires: [
          {
            fire_event_id: null,
            fire_date: '2024-06-15',
            distance_meters: 500,
            in_protected_area: false,
            province: 'Córdoba',
          },
        ],
        evidence: { thumbnails: [] },
        audit_id: 'audit-2',
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

    // Verify N/D shown
    expect(screen.getAllByText('N/D').length).toBeGreaterThanOrEqual(1)

    // Verify no "Ver detalle" / detail navigation button for this fire
    const detailButtons = screen.queryAllByRole('button', { name: /seeDetail|Ver detalle/i })
    expect(detailButtons.length).toBe(0)
  })
})


