/**
 * @file geocode.ts
 * @description Geocoding endpoints.
 */

import { apiClient } from '../api'
import type { GeocodeResponse, GeocodeResult } from '@/types/geocode'

export async function geocodeLocation(query: string): Promise<GeocodeResponse> {
  const response = await apiClient.get<GeocodeResponse>('/audit/geocode', {
    params: { q: query },
  })
  return response.data
}

export async function reverseGeocode(lat: number, lon: number): Promise<GeocodeResult> {
  const response = await apiClient.get<GeocodeResponse>('/audit/reverse-geocode', {
    params: { lat, lon },
  })
  return response.data.result
}
