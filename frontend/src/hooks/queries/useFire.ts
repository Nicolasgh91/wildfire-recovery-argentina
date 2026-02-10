/**
 * @file useFire.ts
 * @description Hook for fire detail.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getFireById } from '@/services/endpoints/fires'
import { queryKeys, QUERY_CONFIG } from '@/lib/queryClient'

export function useFire(id: string) {
  return useQuery({
    queryKey: queryKeys.fires.detail(id),
    queryFn: ({ signal }) => getFireById(id, signal),
    enabled: !!id,
  })
}

export function usePrefetchFire() {
  const queryClient = useQueryClient()
  return (id: string) => {
    if (!id) return Promise.resolve()
    return queryClient.prefetchQuery({
      queryKey: queryKeys.fires.detail(id),
      queryFn: ({ signal }) => getFireById(id, signal),
      staleTime: QUERY_CONFIG.STALE_TIME,
    })
  }
}