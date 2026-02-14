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

export type ExplorationGenerateResponse = {
  job_id: string
  status: string
  items_count: number
  credits_spent: number
  credits_remaining: number
}

export type ExplorationGenerationStatusResponse = {
  job_id: string
  investigation_id: string
  status: 'queued' | 'processing' | 'ready' | 'failed'
  progress_done: number
  progress_total: number
  progress_pct: number
  failed_items: number
  updated_at?: string | null
}

export type ExplorationAsset = {
  id: string
  item_id: string
  signed_url: string
  mime?: string | null
  width?: number | null
  height?: number | null
  sha256?: string | null
  generated_at?: string | null
  target_date: string
  kind: ExplorationItemKind
  status: ExplorationItemStatus
}

export type ExplorationAssetsResponse = {
  assets: ExplorationAsset[]
}
