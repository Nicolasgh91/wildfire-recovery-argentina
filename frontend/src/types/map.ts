import type { FireStatus } from './fire'

export type FireMapItem = {
  id: string
  title: string
  lat: number
  lon: number
  severity?: 'high' | 'medium' | 'low'
  province?: string | null
  status?: FireStatus
  date?: string
  hectares?: number | null
  in_protected_area?: boolean
  overlap_percentage?: number | null
  protected_area_name?: string | null
  count_protected_areas?: number | null
}
