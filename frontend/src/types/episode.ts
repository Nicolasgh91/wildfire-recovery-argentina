export type EpisodeStatus = 'active' | 'monitoring' | 'extinct' | 'closed'

export type EpisodeSlide = {
  type: string
  thumbnail_url?: string | null
  url?: string | null
  satellite_image_id?: string | null
  generated_at?: string | null
}

export type EpisodeListItem = {
  id: string
  status?: EpisodeStatus
  start_date: string
  end_date?: string | null
  last_seen_at?: string | null
  centroid_lat?: number | null
  centroid_lon?: number | null
  provinces?: string[] | null
  event_count: number
  detection_count: number
  frp_sum?: number | null
  frp_max?: number | null
  estimated_area_hectares?: number | null
  gee_candidate?: boolean
  gee_priority?: number | null
  slides_data?: EpisodeSlide[] | null
  /** pending | processing | ready | failed */
  slides_status?: string | null
  representative_event_id?: string | null
  is_recent?: boolean
  recent_days?: number | null
  recovery_status?: string | null
  is_potential_violation?: boolean
}

export type EpisodeListResponse = {
  total: number
  page: number
  page_size: number
  total_pages: number
  episodes: EpisodeListItem[]
}
