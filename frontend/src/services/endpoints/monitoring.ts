import { apiClient } from '../api'

export interface MonthlyNDVI {
  month: number
  date: string
  ndvi_mean: number
  recovery_percentage: number | null
  cloud_cover_pct: number | null
}

export interface RecoveryResponse {
  fire_event_id: string
  fire_date: string
  fire_location: { lat: number; lon: number }
  baseline_ndvi: number | null
  current_ndvi: number | null
  months_monitored: number
  recovery_status: string
  recovery_percentage: number | null
  anomaly_detected: string | null
  monitoring_data: MonthlyNDVI[]
  query_duration_ms: number
  /** Mensaje opcional, p. ej. cuando recovery_status es "pending" */
  message?: string | null
}

export interface LandUseChangeItem {
  id: string
  change_detected_at: string
  months_after_fire: number | null
  change_type: string
  change_severity: string | null
  affected_area_hectares: number | null
  is_potential_violation: boolean
  violation_confidence: string | null
  status: string
  notes: string | null
}

export interface LandUseChangesResponse {
  fire_event_id: string
  total_changes: number
  violation_count: number
  changes: LandUseChangeItem[]
}

export async function getRecoveryTimeline(
  fireEventId: string,
  signal?: AbortSignal,
): Promise<RecoveryResponse> {
  const { data } = await apiClient.get<RecoveryResponse>(
    `/monitoring/recovery/${fireEventId}`,
    { signal },
  )
  return data
}

/** Fase 6: recovery agregado por episodio (todos los eventos del episodio). */
export async function getRecoveryByEpisode(
  episodeId: string,
  signal?: AbortSignal,
): Promise<RecoveryResponse> {
  const { data } = await apiClient.get<RecoveryResponse>(
    `/monitoring/recovery/by-episode/${episodeId}`,
    { signal },
  )
  return data
}

export async function getLandUseChanges(
  fireEventId: string,
  signal?: AbortSignal,
): Promise<LandUseChangesResponse> {
  const { data } = await apiClient.get<LandUseChangesResponse>(
    `/monitoring/land-use-changes/${fireEventId}`,
    { signal },
  )
  return data
}
