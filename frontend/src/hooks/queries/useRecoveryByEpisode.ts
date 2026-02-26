/**
 * @file useRecoveryByEpisode.ts
 * @description Hook for aggregated recovery timeline by episode (Fase 6).
 */

import { useQuery } from '@tanstack/react-query'
import { getRecoveryByEpisode } from '@/services/endpoints/monitoring'
import { queryKeys } from '@/lib/queryClient'

export function useRecoveryByEpisode(episodeId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.monitoring.recoveryByEpisode(episodeId),
    queryFn: ({ signal }) => getRecoveryByEpisode(episodeId, signal),
    enabled: !!episodeId && enabled,
  })
}
