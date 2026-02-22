export type AuditRequest = {
  lat: number
  lon: number
  radius_meters?: number
  cadastral_id?: string
  metadata?: {
    is_test?: boolean
  }
}

export type AuditFire = {
  fire_event_id: string
  fire_date: string
  distance_meters: number
  in_protected_area: boolean
  prohibition_until: string
  years_remaining: number
  province?: string | null
  avg_confidence?: number | null
  estimated_area_hectares?: number | null
  protected_area_names?: string[]
  protected_area_categories?: string[]
}

export type EvidenceThumbnail = {
  fire_event_id: string
  thumbnail_url: string
  acquisition_date?: string | null
  image_type?: string | null
  gee_system_index?: string | null
}

export type AuditEvidence = {
  thumbnails: EvidenceThumbnail[]
}

export type AuditResponse = {
  audit_id: string
  audit_hash: string
  is_prohibited: boolean
  prohibition_until?: string | null
  fires_found: number
  fires: AuditFire[]
  evidence: AuditEvidence
  location: Record<string, number>
  radius_meters: number
  cadastral_id?: string | null
  warnings?: string[]
  generated_at?: string
}
