import type { HistoricalReportResponse, JudicialReportResponse } from '@/types/report'

export type ReportRequestKind = 'judicial' | 'historical'

export type PendingReportApproval = {
  reportType: ReportRequestKind
  requiredCredits: number
  requestedAt: string
  summary: string
}

export type ReportOutcome = {
  reportType: ReportRequestKind
  requiredCredits: number
  response: JudicialReportResponse | HistoricalReportResponse
}
