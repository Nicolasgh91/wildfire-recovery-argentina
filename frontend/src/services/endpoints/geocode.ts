/**
 * @file geocode.ts
 * @description Geocoding endpoints.
 */

import { apiClient } from '../api'
import type { GeocodeResponse } from '@/types/geocode'

export async function geocodeLocation(query: string): Promise<GeocodeResponse> {
  const response = await apiClient.get<GeocodeResponse>('/audit/geocode', {
    params: { q: query },
  })
  return response.data
}
