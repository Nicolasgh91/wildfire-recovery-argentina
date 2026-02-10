import { describe, expect, it } from 'vitest'
import { QUERY_CONFIG, queryClient, queryKeys } from '@/lib/queryClient'

describe('queryClient', () => {
  it('uses the expected default query options', () => {
    const options = queryClient.getDefaultOptions().queries
    expect(options?.staleTime).toBe(QUERY_CONFIG.STALE_TIME)
    expect(options?.gcTime).toBe(QUERY_CONFIG.GC_TIME)
    expect(options?.retry).toBe(3)
    expect(options?.refetchOnWindowFocus).toBe(true)
  })

  it('builds stable query keys', () => {
    expect(queryKeys.fires.all).toEqual(['fires'])
    expect(queryKeys.fires.detail('abc')).toEqual(['fires', 'detail', 'abc'])
    expect(queryKeys.fires.list({ province: 'X' })).toEqual([
      'fires',
      'list',
      { province: 'X' },
    ])
  })
})