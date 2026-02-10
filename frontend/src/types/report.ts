export type ReportMetadata = {
  report_id: string
  report_type: string
  fire_event_id?: string | null
  protected_area_id?: string | null
  generated_at: string
  valid_until: string
  verification_hash: string
  pdf_url: string
  download_url: string
}

export type JudicialReportRequest = {
  fire_event_id: string
  report_type?: string
  include_climate?: boolean
  include_imagery?: boolean
  language?: 'es'
  requester_name?: string | null
  case_reference?: string | null
}

export type HistoricalReportRequest = {
  protected_area_id?: string | null
  protected_area_name?: string | null
  start_date: string
  end_date: string
  include_monthly_images?: boolean
  max_images?: number
  language?: 'es'
}

export type JudicialReportResponse = {
  success: boolean
  report: ReportMetadata
  query_duration_ms: number
}

export type HistoricalReportResponse = {
  success: boolean
  fires_included: number
  date_range: {
    start: string
    end: string
  }
  report: ReportMetadata
  query_duration_ms: number
}

export type VerifyReportResponse = {
  is_valid: boolean
  report_id: string
  original_hash: string
  verified_at: string
  message: string
}