/**
 * @file explorations.ts
 * @description Exploration endpoints.
 */

import { apiClient } from '../api'
import type {
  ExplorationCreateRequest,
  ExplorationItemCreateRequest,
  ExplorationItemResponse,
  ExplorationQuoteResponse,
  ExplorationResponse,
  ExplorationUpdateRequest,
} from '@/types/exploration'

export async function createExploration(
  payload: ExplorationCreateRequest,
): Promise<ExplorationResponse> {
  const response = await apiClient.post<ExplorationResponse>('/explorations', payload)
  return response.data
}

export async function updateExploration(
  explorationId: string,
  payload: ExplorationUpdateRequest,
): Promise<ExplorationResponse> {
  const response = await apiClient.patch<ExplorationResponse>(
    `/explorations/${explorationId}`,
    payload,
  )
  return response.data
}

export async function addExplorationItem(
  explorationId: string,
  payload: ExplorationItemCreateRequest,
): Promise<ExplorationItemResponse> {
  const response = await apiClient.post<ExplorationItemResponse>(
    `/explorations/${explorationId}/items`,
    payload,
  )
  return response.data
}

export async function deleteExplorationItem(
  explorationId: string,
  itemId: string,
): Promise<void> {
  await apiClient.delete(`/explorations/${explorationId}/items/${itemId}`)
}

export async function getExplorationQuote(
  explorationId: string,
): Promise<ExplorationQuoteResponse> {
  const response = await apiClient.post<ExplorationQuoteResponse>(
    `/explorations/${explorationId}/quote`,
  )
  return response.data
}
