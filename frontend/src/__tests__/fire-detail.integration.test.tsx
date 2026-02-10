import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { getFireTitle } from '@/types/fire'

const RUN_INTEGRATION = process.env.RUN_FRONTEND_INTEGRATION === '1'
const API_BASE_URL = process.env.VITE_API_BASE_URL
const API_KEY = process.env.VITE_API_KEY || process.env.VITE_SUPABASE_ANON_KEY

const testFn = RUN_INTEGRATION && API_BASE_URL && API_KEY ? it : it.skip

describe('FireDetailPage integration', () => {
  beforeAll(() => {
    if (!RUN_INTEGRATION || !API_BASE_URL || !API_KEY) return
    vi.stubEnv('VITE_API_BASE_URL', API_BASE_URL)
    vi.stubEnv('VITE_API_KEY', API_KEY)
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', API_KEY)
    vi.stubEnv('VITE_USE_SUPABASE_JWT', 'false')
    vi.stubEnv('VITE_SUPABASE_URL', process.env.VITE_SUPABASE_URL || 'https://example.supabase.co')
  })

  afterAll(() => {
    vi.unstubAllEnvs()
  })

  testFn('renders fire detail from backend', async () => {
    vi.resetModules()
    const { getFires } = await import('@/services/endpoints/fires')
    const { default: FireDetailPage } = await import('@/pages/FireDetail')
    const { I18nProvider } = await import('@/context/LanguageContext')

    const list = await getFires({ page: 1, page_size: 1 })
    expect(list.fires.length).toBeGreaterThan(0)

    const fire = list.fires[0]
    const title = getFireTitle(fire.department ?? undefined, fire.province ?? undefined)

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <I18nProvider>
          <MemoryRouter initialEntries={[`/fires/${fire.id}`]}>
            <Routes>
              <Route path="/fires/:id" element={<FireDetailPage />} />
            </Routes>
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>,
    )

    await waitFor(
      () => {
        expect(screen.getByText(title)).toBeInTheDocument()
      },
      { timeout: 15000 }
    )

    expect(
      await screen.findByText(/Calidad de datos|Data quality/i, {}, { timeout: 15000 })
    ).toBeInTheDocument()
  }, 20000)
})
