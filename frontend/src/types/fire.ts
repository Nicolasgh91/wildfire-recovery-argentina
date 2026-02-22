export type FireStatus = 'active' | 'controlled' | 'monitoring' | 'extinguished'

export type FireSlide = {
  type: string
  title: string
  url: string
  description?: string | null
  date?: string | null
}

export type FireEventListItem = {
  id: string
  start_date: string
  end_date: string
  duration_hours?: number | null
  centroid?: { latitude: number; longitude: number } | null
  province?: string | null
  department?: string | null
  total_detections: number
  avg_confidence?: number | null
  max_frp?: number | null
  estimated_area_hectares?: number | null
  is_significant: boolean
  has_satellite_imagery: boolean
  protected_area_name?: string | null
  in_protected_area: boolean
  overlap_percentage?: number | null
  count_protected_areas?: number | null
  status?: FireStatus
  slides_data?: FireSlide[] | null
}

export type PaginationMeta = {
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export type FireListResponse = {
  fires: FireEventListItem[]
  pagination: PaginationMeta
  filters_applied?: Record<string, unknown>
  generated_at?: string
}

export type FireSearchItem = {
  id: string
  start_date: string
  end_date: string
  province?: string | null
  department?: string | null
  estimated_area_hectares?: number | null
  avg_confidence?: number | null
  quality_score?: number | null
  total_detections: number
  has_satellite_imagery: boolean
  centroid?: { latitude: number; longitude: number } | null
  status?: FireStatus
}

export type FireSearchResponse = {
  fires: FireSearchItem[]
  pagination: PaginationMeta
  filters_applied?: Record<string, unknown>
  generated_at?: string
}

export type ExplorationPreviewTimeline = {
  before: string[]
  during: string[]
  after: string[]
}

export type ExplorationPreviewResponse = {
  fire_event_id: string
  province?: string | null
  department?: string | null
  start_date: string
  end_date: string
  extinguished_at?: string | null
  centroid?: { latitude: number; longitude: number } | null
  bbox?: { west: number; south: number; east: number; north: number } | null
  perimeter_geojson?: Record<string, unknown> | null
  estimated_area_hectares?: number | null
  duration_days?: number | null
  has_satellite_imagery: boolean
  timeline: ExplorationPreviewTimeline
}

export type FireStatsResponse = {
  period: {
    from: string
    to: string
  }
  stats: {
    total_fires: number
    active_fires: number
    historical_fires: number
    total_detections: number
    total_hectares: number
    avg_hectares: number
    median_hectares: number
    avg_confidence: number
    fires_in_protected: number
    protected_percentage: number
    significant_fires: number
    significant_percentage: number
    top_frp_fires: Array<{
      id: string
      max_frp?: number | null
      province?: string | null
      start_date?: string | null
    }>
    by_province: Array<{
      name: string
      fire_count: number
      latest_fire?: string | null
    }>
    by_month: Record<string, number>
  }
  ytd_comparison?: YtdComparison
  generated_at?: string
}

export type ExportRequestStatus = {
  status: string
  message: string
  job_id?: string | null
  total_records?: number | null
}

export type MetricComparison = {
  current: number
  previous: number
  delta: number
  delta_pct?: number | null
}

export type YtdComparison = {
  total_fires: MetricComparison
  total_hectares: MetricComparison
  total_detections: MetricComparison
  avg_confidence: MetricComparison
  significant_fires: MetricComparison
}

export type FireSortValue =
  | 'start_date_desc'
  | 'start_date_asc'
  | 'area_desc'
  | 'area_asc'
  | 'frp_desc'
  | 'frp_asc'

export type FireStatusScope = 'active' | 'historical' | 'all'

export type FireFilters = {
  province?: string
  status_scope?: FireStatusScope
  date_from?: string
  date_to?: string
  search?: string
  sort_by?: string
  sort_desc?: boolean | string
  page?: number | string
  page_size?: number | string
  format?: string
}

export type FireFiltersState = {
  province: string
  status_scope: FireStatusScope
  date_from: string
  date_to: string
  search: string
  sort_by: FireSortValue
  page: number
  page_size: number
}

export type FireDetection = {
  id: string
  satellite: string
  detected_at: string
  latitude: number
  longitude: number
  frp?: number | null
  confidence?: number | null
}

export type ProtectedAreaBrief = {
  id: string
  name: string
  category: string
  prohibition_until?: string | null
}

export type FireDetail = FireEventListItem & {
  avg_frp?: number | null
  sum_frp?: number | null
  has_legal_analysis?: boolean
  processing_error?: string | null
  protected_areas?: ProtectedAreaBrief[]
  created_at?: string
  updated_at?: string | null
}

export type FireDetailResponse = {
  source_type?: 'event' | 'episode'
  episode_id?: string | null
  fire: FireDetail
  detections: FireDetection[]
  related_fires_count: number
  event_count?: number | null
  last_seen_at?: string | null
}

type SeverityConfig = {
  label: string
  badgeClasses: string
  iconColor: string
}

const FRP_MEDIUM_THRESHOLD = 20
const FRP_HIGH_THRESHOLD = 50

export function getSeverityConfig(frp?: number | null): SeverityConfig {
  if (frp === null || frp === undefined || Number.isNaN(frp)) {
    return {
      label: 'Baja',
      badgeClasses: 'border-slate-200 bg-slate-100 text-slate-600',
      iconColor: 'text-slate-500',
    }
  }

  if (frp >= FRP_HIGH_THRESHOLD) {
    return {
      label: 'Alta',
      badgeClasses: 'border-red-200 bg-red-100 text-red-700',
      iconColor: 'text-red-600',
    }
  }

  if (frp >= FRP_MEDIUM_THRESHOLD) {
    return {
      label: 'Media',
      badgeClasses: 'border-amber-200 bg-amber-100 text-amber-700',
      iconColor: 'text-amber-600',
    }
  }

  return {
    label: 'Baja',
    badgeClasses: 'border-emerald-200 bg-emerald-100 text-emerald-700',
    iconColor: 'text-emerald-600',
  }
}

export function formatDate(value?: string | null): string {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'N/A'
  return date.toLocaleDateString('es-AR')
}

export function formatHectares(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  const formatter = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })
  return `${formatter.format(value)} ha`
}

export function getFireTitle(
  department?: string | null,
  province?: string | null
): string {
  const dept = department?.trim()
  const prov = province?.trim()

  if (dept && prov) {
    return `Incendio en ${dept}, ${prov}`
  }

  if (prov) {
    return `Incendio en ${prov}`
  }

  if (dept) {
    return `Incendio en ${dept}`
  }

  return 'Incendio sin ubicacion'
}
