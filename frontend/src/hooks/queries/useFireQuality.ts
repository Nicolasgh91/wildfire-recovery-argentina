/**
 * @file useFireQuality.ts
 * @description Hook for fire quality metrics.
 */

import { useQuery } from '@tanstack/react-query'
import { getFireQuality } from '@/services/endpoints/quality'
import { queryKeys } from '@/lib/queryClient'

export function useFireQuality(id: string) {
  return useQuery({
    queryKey: queryKeys.quality.fire(id),
    queryFn: ({ signal }) => getFireQuality(id, signal),
    enabled: !!id,
  })
}
