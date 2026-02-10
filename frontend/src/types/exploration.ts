export type ExplorationStatus = 'draft' | 'quoted' | 'processing' | 'ready' | 'failed'

export type ExplorationItemStatus = 'pending' | 'queued' | 'generated' | 'failed'

export type ExplorationItemKind = 'pre' | 'post'

export type ExplorationCreateRequest = {
  fire_event_id: string
  title?: string | null
}

export type ExplorationUpdateRequest = {
  title?: string | null
}

export type ExplorationItemCreateRequest = {
  kind: ExplorationItemKind
  target_date: string
  sensor?: string | null
  aoi?: Record<string, unknown> | null
  geometry_ref?: string | null
  visualization_params?: Record<string, unknown> | null
}

export type ExplorationItemResponse = {
  id: string
  kind: ExplorationItemKind
  target_date: string
  sensor?: string | null
  aoi?: Record<string, unknown> | null
  geometry_ref?: string | null
  visualization_params?: Record<string, unknown> | null
  status: ExplorationItemStatus
  error?: string | null
  created_at: string
  updated_at: string
}

export type ExplorationResponse = {
  id: string
  fire_event_id?: string | null
  title?: string | null
  status: ExplorationStatus
  created_at: string
  updated_at: string
  items: ExplorationItemResponse[]
}

export type ExplorationQuoteResponse = {
  items_count: number
  unit_price_ars: number
  total_price_ars: number
  credits_required: number
  suggestions: string[]
}
