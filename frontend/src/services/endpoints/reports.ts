/**
 * @file reports.ts
 * @description Report endpoints.
 */

import { apiClient } from '../api'
import type {
  HistoricalReportRequest,
  HistoricalReportResponse,
  JudicialReportRequest,
  JudicialReportResponse,
  ReportMetadata,
  VerifyReportResponse,
} from '@/types/report'

export async function requestJudicialReport(
  payload: JudicialReportRequest,
  idempotencyKey?: string
): Promise<JudicialReportResponse> {
  const response = await apiClient.post<JudicialReportResponse>('/reports/judicial', payload, {
    headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : undefined,
  })
  return response.data
}

export async function requestHistoricalReport(
  payload: HistoricalReportRequest,
  idempotencyKey?: string
): Promise<HistoricalReportResponse> {
  const response = await apiClient.post<HistoricalReportResponse>('/reports/historical', payload, {
    headers: idempotencyKey ? { 'X-Idempotency-Key': idempotencyKey } : undefined,
  })
  return response.data
}

export async function verifyReport(
  reportId: string,
  hashToVerify: string
): Promise<VerifyReportResponse> {
  const response = await apiClient.get<VerifyReportResponse>(`/reports/${reportId}/verify`, {
    params: { hash_to_verify: hashToVerify },
  })
  return response.data
}

export type ReportStatusResponse = {
  status: 'processing' | 'completed' | 'failed'
  report?: ReportMetadata
  message?: string
}

export async function getReportStatus(reportId: string): Promise<ReportStatusResponse> {
  const response = await apiClient.get<ReportStatusResponse>(`/reports/${reportId}`)
  return response.data
}
