export type QualityClass = 'high' | 'medium' | 'low'

export type SeverityLevel = 'low' | 'medium' | 'high'

export type QualityLimitation = {
  code: string
  description: string
  severity: SeverityLevel
}

export type QualitySource = {
  source_name: string
  source_type?: string | null
  spatial_resolution_meters?: number | null
  temporal_resolution_hours?: number | null
  coverage_area?: string | null
  typical_accuracy_percentage?: number | null
  known_limitations?: string | null
  is_admissible_in_court?: boolean | null
  legal_precedent_cases?: string[] | null
  data_provider?: string | null
  provider_url?: string | null
  documentation_url?: string | null
  last_updated?: string | null
  is_used?: boolean | null
}

export type QualityMetrics = {
  reliability_score: number
  classification: QualityClass
  confidence_score: number
  imagery_score: number
  climate_score: number
  independent_score: number
  avg_confidence: number
  total_detections: number
  independent_sources: number
  has_imagery: boolean
  has_climate: boolean
  has_ndvi: boolean
  score_calculated_at: string
}

export type QualityResponse = {
  fire_event_id: string
  start_date: string
  province?: string | null
  metrics: QualityMetrics
  limitations: QualityLimitation[]
  sources: QualitySource[]
  warnings: string[]
}
