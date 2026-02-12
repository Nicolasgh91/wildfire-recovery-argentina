/**
 * @file fires.ts
 * @description Fire endpoints.
 */

import { apiClient } from '../api'
import type {
  ExportRequestStatus,
  FireDetailResponse,
  FireFilters,
  FireListResponse,
  FireStatsResponse,
} from '@/types/fire'

export type FireProvince = {
  name: string
  fire_count: number
  latest_fire: string | null
}

export type FireProvincesResponse = {
  provinces: FireProvince[]
  total: number
}

export async function getFires(
  filters?: FireFilters,
  signal?: AbortSignal
): Promise<FireListResponse> {
  const response = await apiClient.get<FireListResponse>('/fires', {
    params: filters,
    signal,
  })
  return response.data
}

export async function getFireById(
  id: string,
  signal?: AbortSignal
): Promise<FireDetailResponse> {
  const response = await apiClient.get<FireDetailResponse>(`/fires/${id}`, {
    signal,
  })
  return response.data
}

export async function getFireStats(
  filters?: FireFilters,
  signal?: AbortSignal
): Promise<FireStatsResponse> {
  const response = await apiClient.get<FireStatsResponse>('/fires/stats', {
    params: filters,
    signal,
  })
  return response.data
}

export async function getActiveFires(
  limit: number = 20,
  signal?: AbortSignal
): Promise<FireListResponse> {
  const response = await apiClient.get<FireListResponse>('/fires/active', {
    params: { limit },
    signal,
  })
  return response.data
}

export async function exportFires(
  filters?: FireFilters
): Promise<Blob | ExportRequestStatus> {
  const response = await apiClient.get('/fires/export', {
    params: filters,
    responseType: 'blob',
  })

  const contentType = response.headers?.['content-type'] || ''
  if (response.status === 202 || contentType.includes('application/json')) {
    const text = await (response.data as Blob).text()
    return JSON.parse(text) as ExportRequestStatus
  }

  return response.data as Blob
}

export async function getFireProvinces(
  signal?: AbortSignal,
): Promise<FireProvincesResponse> {
  const response = await apiClient.get<FireProvincesResponse>('/fires/provinces', {
    signal,
  })
  return response.data
}
