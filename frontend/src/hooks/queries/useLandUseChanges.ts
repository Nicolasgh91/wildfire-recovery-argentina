import { useQuery } from '@tanstack/react-query'
import { getLandUseChanges } from '@/services/endpoints/monitoring'
import { queryKeys } from '@/lib/queryClient'

export function useLandUseChanges(fireEventId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.monitoring.landUseChanges(fireEventId),
    queryFn: ({ signal }) => getLandUseChanges(fireEventId, signal),
    enabled: !!fireEventId && enabled,
  })
}
