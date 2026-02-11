export type AuditSearchBBox = {
  minx: number
  miny: number
  maxx: number
  maxy: number
}

export type AuditSearchResolvedPlace = {
  label: string
  type: 'province' | 'protected_area' | 'address'
  bbox?: AuditSearchBBox | null
  point?: { lat: number; lon: number } | null
}

export type AuditSearchEpisode = {
  id: string
  start_date: string
  end_date?: string | null
  status?: string | null
  provinces?: string[] | null
  estimated_area_hectares?: number | null
  detection_count?: number | null
  frp_max?: number | null
}

export type AuditSearchResponse = {
  resolved_place: AuditSearchResolvedPlace
  episodes: AuditSearchEpisode[]
  total: number
  date_range: {
    earliest?: string | null
    latest?: string | null
  }
}
