/**
 * @file quality.ts
 * @description Quality endpoints.
 */

import { apiClient } from '../api'
import type { QualityResponse } from '@/types/quality'

export async function getFireQuality(
  fireEventId: string,
  signal?: AbortSignal
): Promise<QualityResponse> {
  const response = await apiClient.get<QualityResponse>(
    `/quality/fire-event/${fireEventId}`,
    { signal }
  )
  return response.data
}
