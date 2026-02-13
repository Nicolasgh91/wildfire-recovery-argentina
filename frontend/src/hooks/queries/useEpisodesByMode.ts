/**
 * @file useEpisodesByMode.ts
 * @description Hook for episodes by mode (active/recent).
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getEpisodes, type EpisodeListMode } from '@/services/endpoints/episodes'
import { queryKeys } from '@/lib/queryClient'


export function useEpisodesByMode(
  mode: EpisodeListMode,
  limit: number = 20,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: queryKeys.episodes.mode(mode, limit),
    queryFn: ({ signal }) =>
      getEpisodes({ mode, page: 1, page_size: limit }, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  })
}
