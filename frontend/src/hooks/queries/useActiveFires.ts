/**
 * @file useActiveFires.ts
 * @description Hook for active fires with thumbnails (Home).
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getActiveFires } from '@/services/endpoints/fires'
import { queryKeys } from '@/lib/queryClient'

export function useActiveFires(limit: number = 20) {
  return useQuery({
    queryKey: queryKeys.fires.active(limit),
    queryFn: ({ signal }) => getActiveFires(limit, signal),
    placeholderData: keepPreviousData,
  })
}
