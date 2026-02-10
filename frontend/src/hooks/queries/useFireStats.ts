/**
 * @file useFireStats.ts
 * @description Hook para estadisticas de incendios.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getFireStats } from '@/services/endpoints/fires'
import { queryKeys } from '@/lib/queryClient'
import type { FireFilters } from '@/types/fire'

export function useFireStats(filters?: FireFilters) {
  const safeFilters = filters || {}
  return useQuery({
    queryKey: queryKeys.fires.stats(safeFilters),
    queryFn: ({ signal }) => getFireStats(safeFilters, signal),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
    structuralSharing: true,
  })
}
