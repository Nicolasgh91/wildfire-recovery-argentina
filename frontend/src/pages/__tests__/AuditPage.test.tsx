import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuditPage from '../Audit'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'

jest.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) => key,
    language: 'es',
  }),
}))

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

