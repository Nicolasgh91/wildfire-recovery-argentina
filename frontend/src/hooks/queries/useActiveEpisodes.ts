/**
 * @file useActiveEpisodes.ts
 * @description Hook for active episodes with thumbnails (Home).
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getEpisodes } from '@/services/endpoints/episodes'
import { queryKeys } from '@/lib/queryClient'

export function useActiveEpisodes(limit: number = 20) {
  return useQuery({
    queryKey: queryKeys.episodes.active(limit),
    queryFn: ({ signal }) =>
      getEpisodes({ mode: 'active', page: 1, page_size: limit }, signal),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    cacheTime: 30 * 60 * 1000,
  })
}
