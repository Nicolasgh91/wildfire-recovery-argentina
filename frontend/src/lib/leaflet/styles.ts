import type { PathOptions } from 'leaflet'

export type MapSeverity = 'low' | 'medium' | 'high' | 'critical'
export type MapStatus = 'active' | 'controlled' | 'monitoring' | 'extinguished'

export const SEVERITY_COLORS: Record<MapSeverity, string> = {
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#7f1d1d',
}

export const STATUS_COLORS: Record<MapStatus, string> = {
  active: '#ef4444',
  controlled: '#f59e0b',
  monitoring: '#10b981',
  extinguished: '#6b7280',
}

export const PROTECTED_AREA_STYLE: PathOptions = {
  color: '#0f766e',
  fillColor: '#99f6e4',
  weight: 1,
  opacity: 0.9,
  fillOpacity: 0.2,
  dashArray: '4 4',
}

export const PROTECTED_AREA_HOVER_STYLE: PathOptions = {
  weight: 2,
  fillOpacity: 0.35,
}

type EpisodeLike = {
  severity?: MapSeverity
  status?: MapStatus
}

export function getEpisodeStyle(episode: EpisodeLike): PathOptions {
  const severity = episode.severity ?? 'medium'
  const status = episode.status ?? 'active'

  return {
    fillColor: SEVERITY_COLORS[severity],
    fillOpacity: 0.6,
    color: STATUS_COLORS[status],
    weight: 2,
    opacity: 1,
  }
}

export function getHeatmapColor(intensity: number): [number, number, number, number] {
  if (intensity > 0.8) return [239, 68, 68, 200]
  if (intensity > 0.6) return [249, 115, 22, 180]
  if (intensity > 0.4) return [245, 158, 11, 160]
  if (intensity > 0.2) return [234, 179, 8, 140]
  return [34, 197, 94, 120]
}
