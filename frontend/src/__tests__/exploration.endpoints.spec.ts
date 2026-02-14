import { describe, expect, it, vi, beforeEach } from 'vitest'

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}))
const { apiPost } = vi.hoisted(() => ({
  apiPost: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  apiClient: {
    get: apiGet,
    post: apiPost,
  },
}))

import {
  generateExploration,
  getExplorationAssets,
  getExplorationGenerationStatus,
} from '../services/endpoints/explorations'

describe('exploration endpoints', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
  })

  it('requests generation status endpoint with exploration and job ids', async () => {
    apiGet.mockResolvedValue({
      data: {
        job_id: 'job-1',
        investigation_id: 'exp-1',
        status: 'processing',
        progress_done: 1,
        progress_total: 2,
        progress_pct: 50,
        failed_items: 0,
      },
    })

    const response = await getExplorationGenerationStatus('exp-1', 'job-1')

    expect(apiGet).toHaveBeenCalledWith(
      '/explorations/exp-1/generate/job-1',
      expect.any(Object),
    )
    expect(response.status).toBe('processing')
    expect(response.progress_pct).toBe(50)
  })

  it('requests exploration assets endpoint', async () => {
    apiGet.mockResolvedValue({
      data: {
        assets: [
          {
            id: 'asset-1',
            item_id: 'item-1',
            signed_url: 'https://example.com/asset.png',
            target_date: '2024-01-01T00:00:00Z',
            kind: 'pre',
            status: 'generated',
          },
        ],
      },
    })

    const response = await getExplorationAssets('exp-1')

    expect(apiGet).toHaveBeenCalledWith('/explorations/exp-1/assets', expect.any(Object))
    expect(response.assets).toHaveLength(1)
    expect(response.assets[0].id).toBe('asset-1')
  })

  it('requests exploration generate endpoint with Idempotency-Key header', async () => {
    apiPost.mockResolvedValue({
      data: {
        job_id: 'job-123',
        status: 'queued',
        items_count: 3,
        credits_spent: 3,
        credits_remaining: 10,
      },
    })

    const response = await generateExploration('exp-1', 'idem-123')

    expect(apiPost).toHaveBeenCalledWith(
      '/explorations/exp-1/generate',
      {},
      expect.objectContaining({
        headers: expect.objectContaining({
          'Idempotency-Key': 'idem-123',
        }),
      }),
    )
    expect(response.job_id).toBe('job-123')
  })
})
