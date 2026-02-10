/**
 * @file fire-events.ts
 * @description Fire events endpoints for exploration.
 */

import { apiClient } from '../api'
import type { ExplorationPreviewResponse, FireSearchResponse } from '@/types/fire'

export type FireEventSearchParams = {
  province?: string[] | string
  date_from?: string
  date_to?: string
  q?: string
  bbox?: string
  page?: number
  page_size?: number
}

export async function searchFireEvents(
  params?: FireEventSearchParams,
  signal?: AbortSignal,
): Promise<FireSearchResponse> {
  const response = await apiClient.get<FireSearchResponse>('/fire-events/search', {
    params,
    signal,
  })
  return response.data
}

export async function getExplorationPreview(
  fireEventId: string,
  signal?: AbortSignal,
): Promise<ExplorationPreviewResponse> {
  const response = await apiClient.get<ExplorationPreviewResponse>(
    `/fire-events/${fireEventId}/exploration-preview`,
    { signal },
  )
  return response.data
}
