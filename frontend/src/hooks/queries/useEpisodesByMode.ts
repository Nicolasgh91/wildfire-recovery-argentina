/**
 * @file useEpisodesByMode.ts
 * @description Hook for episodes by mode (active/recent).
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getEpisodes, type EpisodeListMode, type EpisodeListParams } from '@/services/endpoints/episodes'
import { queryKeys } from '@/lib/queryClient'

const EPISODE_TIMEOUT_MS = 15_000

export function useEpisodesByMode(
  mode: EpisodeListMode,
  limit: number = 20,
  enabled: boolean = true,
  sortParams?: Pick<EpisodeListParams, 'sort_by' | 'sort_desc'>
) {
  const params: EpisodeListParams = { mode, page: 1, page_size: limit, ...sortParams }
  
  return useQuery({
    queryKey: queryKeys.episodes.mode(mode, limit, sortParams),
    queryFn: ({ signal }) => {
      const timeout = AbortSignal.timeout(EPISODE_TIMEOUT_MS)
      const combined = AbortSignal.any([signal, timeout])
      return getEpisodes(params, combined)
    },
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 1,
  })
}
