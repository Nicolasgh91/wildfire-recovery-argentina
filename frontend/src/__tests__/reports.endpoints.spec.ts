import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiPost } = vi.hoisted(() => ({
  apiPost: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  apiClient: {
    post: apiPost,
  },
}))

import {
  requestHistoricalReport,
  requestJudicialReport,
} from '../services/endpoints/reports'

describe('reports endpoints', () => {
  beforeEach(() => {
    apiPost.mockReset()
  })

  it('sends X-Idempotency-Key in judicial report requests', async () => {
    apiPost.mockResolvedValue({
      data: {
        success: true,
        query_duration_ms: 100,
        report: {
          report_id: 'FG-JUD-1',
          report_type: 'judicial',
          generated_at: '2026-01-01T00:00:00Z',
          valid_until: '2027-01-01T00:00:00Z',
          verification_hash: 'abc',
          pdf_url: '/api/v1/reports/FG-JUD-1',
          download_url: '/api/v1/reports/FG-JUD-1/download',
        },
      },
    })

    await requestJudicialReport(
      {
        fire_event_id: '00000000-0000-0000-0000-000000000000',
        include_climate: true,
        include_imagery: true,
        language: 'es',
      },
      'idem-jud-1',
    )

    expect(apiPost).toHaveBeenCalledWith(
      '/reports/judicial',
      expect.any(Object),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Idempotency-Key': 'idem-jud-1',
        }),
      }),
    )
  })

  it('sends X-Idempotency-Key in historical report requests', async () => {
    apiPost.mockResolvedValue({
      data: {
        success: true,
        fires_included: 0,
        date_range: { start: '2024-01-01', end: '2024-12-31' },
        query_duration_ms: 100,
        report: {
          report_id: 'FG-HIS-1',
          report_type: 'historical',
          generated_at: '2026-01-01T00:00:00Z',
          valid_until: '2027-01-01T00:00:00Z',
          verification_hash: 'abc',
          pdf_url: '/api/v1/reports/FG-HIS-1',
          download_url: '/api/v1/reports/FG-HIS-1/download',
        },
      },
    })

    await requestHistoricalReport(
      {
        protected_area_id: '00000000-0000-0000-0000-000000000000',
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        include_monthly_images: true,
        max_images: 6,
        language: 'es',
      },
      'idem-his-1',
    )

    expect(apiPost).toHaveBeenCalledWith(
      '/reports/historical',
      expect.any(Object),
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Idempotency-Key': 'idem-his-1',
        }),
      }),
    )
  })
})
