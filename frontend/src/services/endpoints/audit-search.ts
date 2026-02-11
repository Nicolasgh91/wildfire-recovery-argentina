/**
 * @file audit-search.ts
 * @description Audit search endpoints (historical episodes).
 */

import { apiClient } from '../api'
import type { AuditSearchResponse } from '@/types/audit-search'

export async function searchAuditEpisodes(
  query: string,
  params?: { limit?: number; radius_km?: number },
): Promise<AuditSearchResponse> {
  const response = await apiClient.get<AuditSearchResponse>('/audit/search', {
    params: { q: query, ...params },
  })
  return response.data
}
