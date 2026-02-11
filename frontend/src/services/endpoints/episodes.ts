/**
 * @file episodes.ts
 * @description Episode endpoints.
 */

import { apiClient } from '../api'
import type { EpisodeListResponse } from '@/types/episode'

export type EpisodeListMode = 'active' | 'recent'

export type EpisodeListParams = {
  mode?: EpisodeListMode
  page?: number
  page_size?: number
  status?: string
  gee_candidate?: boolean
  sort_by?: string
  sort_desc?: boolean
}

export async function getActiveEpisodes(
  limit: number = 20,
  signal?: AbortSignal
): Promise<EpisodeListResponse> {
  const response = await apiClient.get<EpisodeListResponse>('/fire-episodes/active', {
    params: { limit },
    signal,
  })
  return response.data
}

export async function getEpisodes(
  params?: EpisodeListParams,
  signal?: AbortSignal
): Promise<EpisodeListResponse> {
  const response = await apiClient.get<EpisodeListResponse>('/fire-episodes', {
    params,
    signal,
  })
  return response.data
}
