import { useQuery } from '@tanstack/react-query'
import { getLandUseChanges } from '@/services/endpoints/monitoring'
import { queryKeys } from '@/lib/queryClient'

/** F8-02: pass null to disable fetch (e.g. when not authenticated). */
export function useLandUseChanges(fireEventId: string | null) {
  return useQuery({
    queryKey: queryKeys.monitoring.landUseChanges(fireEventId ?? ''),
    queryFn: ({ signal }) => getLandUseChanges(fireEventId!, signal),
    enabled: !!fireEventId,
  })
}
