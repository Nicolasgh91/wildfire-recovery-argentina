import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import ExplorationPage from '@/pages/Exploration'

const searchFireEventsMock = vi.fn()
const getExplorationPreviewMock = vi.fn()
const createExplorationMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    status: 'unauthenticated',
    role: 'anonymous',
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signUpWithEmail: vi.fn(),
    signOut: vi.fn(),
    isAuthenticated: false,
  }),
}))

vi.mock('@/services/endpoints/fire-events', () => ({
  searchFireEvents: (...args: unknown[]) => searchFireEventsMock(...args),
  getExplorationPreview: (...args: unknown[]) => getExplorationPreviewMock(...args),
}))

vi.mock('@/services/endpoints/explorations', () => ({
  addExplorationItem: vi.fn(),
  createExploration: (...args: unknown[]) => createExplorationMock(...args),
  deleteExplorationItem: vi.fn(),
  generateExploration: vi.fn(),
  getExplorationQuote: vi.fn(),
  updateExploration: vi.fn(),
}))

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="fire-map" />,
}))

describe('ExplorationPage auth gating', () => {
  it('opens auth dialog before proceeding when unauthenticated', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    searchFireEventsMock.mockResolvedValue({
      fires: [
        {
          id: 'fire-1',
          start_date: '2024-01-01',
          end_date: '2024-01-02',
          province: 'Chubut',
          department: 'Rawson',
          estimated_area_hectares: 120,
          avg_confidence: null,
          quality_score: 50,
          total_detections: 10,
          has_satellite_imagery: true,
          centroid: { latitude: -42.0, longitude: -65.0 },
          status: 'active',
        },
      ],
      pagination: {
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    })

    getExplorationPreviewMock.mockResolvedValue({
      fire_event_id: 'fire-1',
      province: 'Chubut',
      department: 'Rawson',
      start_date: '2024-01-01',
      end_date: '2024-01-02',
      centroid: { latitude: -42.0, longitude: -65.0 },
      estimated_area_hectares: 120,
      has_satellite_imagery: true,
      timeline: {
        before: ['2023-01-01'],
        during: [],
        after: ['2024-01-15'],
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <I18nProvider>
            <ExplorationPage />
          </I18nProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.click(screen.getByTestId('exploration-btn-search'))

    const selectButton = await screen.findByRole('button', { name: 'Seleccionar' })
    await user.click(selectButton)

    const selectedLabels = await screen.findAllByText('Seleccionado')
    expect(selectedLabels.length).toBeGreaterThan(0)

    const nextButton = screen.getByRole('button', { name: 'Siguiente' })
    await user.click(nextButton)

    const nextButtonStep2 = await screen.findByRole('button', { name: 'Siguiente' })
    await waitFor(() => expect(nextButtonStep2).toBeEnabled())
    await user.click(nextButtonStep2)

    expect(screen.getByText('Acceso requerido para generar el informe')).toBeInTheDocument()
    expect(createExplorationMock).not.toHaveBeenCalled()
  })
})
