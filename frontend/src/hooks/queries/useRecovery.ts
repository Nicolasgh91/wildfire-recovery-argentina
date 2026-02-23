import { useQuery } from '@tanstack/react-query'
import { getRecoveryTimeline } from '@/services/endpoints/monitoring'
import { queryKeys } from '@/lib/queryClient'

export function useRecovery(fireEventId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.monitoring.recovery(fireEventId),
    queryFn: ({ signal }) => getRecoveryTimeline(fireEventId, signal),
    enabled: !!fireEventId && enabled,
  })
}
