import { describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useFireStats } from '@/hooks/queries/useFireStats'

vi.mock('@/services/endpoints/fires', () => ({
  getFireStats: vi.fn(async () => ({
    period: { from: '2026-01-01', to: '2026-01-31' },
    stats: {
      total_fires: 1,
      active_fires: 1,
      historical_fires: 0,
      total_detections: 10,
      total_hectares: 2,
      avg_hectares: 2,
      median_hectares: 2,
      avg_confidence: 80,
      fires_in_protected: 0,
      protected_percentage: 0,
      significant_fires: 0,
      significant_percentage: 0,
      top_frp_fires: [],
      by_province: [],
      by_month: {},
    },
    ytd_comparison: null,
    generated_at: '2026-02-04T00:00:00Z',
  })),
}))

describe('useFireStats', () => {
  it('returns stats payload from API', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useFireStats({ province: 'Cordoba' }), {
      wrapper,
    })

    await waitFor(() => expect(result.current.data).toBeTruthy())
    expect(result.current.data?.stats.total_fires).toBe(1)
  })
})
