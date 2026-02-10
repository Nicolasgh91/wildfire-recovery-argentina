/**
 * @file useFires.ts
 * @description Hook for fires list.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getFires } from '@/services/endpoints/fires'
import { queryKeys } from '@/lib/queryClient'
import type { FireFilters } from '@/types/fire'

export function useFires(filters?: FireFilters) {
  return useQuery({
    queryKey: queryKeys.fires.list(filters || {}),
    queryFn: ({ signal }) => getFires(filters, signal),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
  })
}
