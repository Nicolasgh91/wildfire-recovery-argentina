/**
 * @file shelters.ts
 * @description Shelters and visitor logs endpoints.
 */

import { apiClient } from '../api'
import type { Shelter } from '@/data/mockdata'

export type ShelterListResponse = {
  shelters: Shelter[]
  total?: number
}

export type VisitorLogPayload = {
  shelter_id: string
  visit_date: string
  registration_type: 'day_entry' | 'overnight'
  group_leader_name: string
  contact_email?: string
  contact_phone?: string
  companions: Array<{ full_name: string }>
}

export async function getShelters(): Promise<ShelterListResponse> {
  const response = await apiClient.get<ShelterListResponse>('/shelters')
  return response.data
}

export async function createVisitorLog(payload: VisitorLogPayload): Promise<void> {
  await apiClient.post('/visitor-logs', payload)
}