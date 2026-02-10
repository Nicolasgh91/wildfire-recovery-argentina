/**
 * @file episodes.ts
 * @description Episode endpoints.
 */

import { apiClient } from '../api'
import type { EpisodeListResponse } from '@/types/episode'

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
