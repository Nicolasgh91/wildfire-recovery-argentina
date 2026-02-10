/**
 * @file audit.ts
 * @description Audit endpoints.
 */

import { apiClient } from '../api'
import type { AuditRequest, AuditResponse } from '@/types/audit'

export async function performAudit(payload: AuditRequest): Promise<AuditResponse> {
  const response = await apiClient.post<AuditResponse>('/audit/land-use', payload)
  return response.data
}
