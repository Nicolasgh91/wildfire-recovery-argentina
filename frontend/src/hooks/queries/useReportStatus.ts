/**
 * @file useReportStatus.ts
 * @description Hook para consultar estado de reportes.
 */

import { useQuery } from '@tanstack/react-query'
import { getReportStatus, type ReportStatusResponse } from '@/services/endpoints/reports'

export function useReportStatus(reportId: string, enabled: boolean = true) {
  return useQuery<ReportStatusResponse>({
    queryKey: ['reports', 'status', reportId],
    queryFn: () => getReportStatus(reportId),
    enabled: !!reportId && enabled,
    refetchInterval: enabled ? 5000 : false,
  })
}
