/**
 * @file useReportRequest.ts
 * @description Mutation para solicitar reportes judiciales o históricos.
 */

import { useMutation } from '@tanstack/react-query'
import {
  requestHistoricalReport,
  requestJudicialReport,
} from '@/services/endpoints/reports'
import type {
  HistoricalReportRequest,
  HistoricalReportResponse,
  JudicialReportRequest,
  JudicialReportResponse,
} from '@/types/report'

export type ReportRequestInput =
  | {
      type: 'judicial'
      payload: JudicialReportRequest
      idempotencyKey?: string
    }
  | {
      type: 'historical'
      payload: HistoricalReportRequest
      idempotencyKey?: string
    }

export type ReportRequestResult = JudicialReportResponse | HistoricalReportResponse

export function useReportRequestMutation() {
  return useMutation<ReportRequestResult, Error, ReportRequestInput>({
    mutationFn: async (input) => {
      if (input.type === 'judicial') {
        return requestJudicialReport(input.payload, input.idempotencyKey)
      }
      return requestHistoricalReport(input.payload, input.idempotencyKey)
    },
  })
}
