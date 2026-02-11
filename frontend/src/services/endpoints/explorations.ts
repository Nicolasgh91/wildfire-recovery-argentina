/**
 * @file explorations.ts
 * @description Exploration endpoints.
 */

import { apiClient } from '../api'
import { supabase } from '@/lib/supabase'
import type {
  ExplorationCreateRequest,
  ExplorationGenerateResponse,
  ExplorationItemCreateRequest,
  ExplorationItemResponse,
  ExplorationQuoteResponse,
  ExplorationResponse,
  ExplorationUpdateRequest,
} from '@/types/exploration'

export async function createExploration(
  payload: ExplorationCreateRequest,
): Promise<ExplorationResponse> {
  const headers = await buildAuthHeaders()
  const response = await apiClient.post<ExplorationResponse>('/explorations/', payload, { headers })
  return response.data
}

export async function updateExploration(
  explorationId: string,
  payload: ExplorationUpdateRequest,
): Promise<ExplorationResponse> {
  const headers = await buildAuthHeaders()
  const response = await apiClient.patch<ExplorationResponse>(
    `/explorations/${explorationId}`,
    payload,
    { headers },
  )
  return response.data
}

export async function addExplorationItem(
  explorationId: string,
  payload: ExplorationItemCreateRequest,
): Promise<ExplorationItemResponse> {
  const headers = await buildAuthHeaders()
  const response = await apiClient.post<ExplorationItemResponse>(
    `/explorations/${explorationId}/items`,
    payload,
    { headers },
  )
  return response.data
}

export async function deleteExplorationItem(
  explorationId: string,
  itemId: string,
): Promise<void> {
  const headers = await buildAuthHeaders()
  await apiClient.delete(`/explorations/${explorationId}/items/${itemId}`, {
    headers,
  })
}

export async function getExplorationQuote(
  explorationId: string,
): Promise<ExplorationQuoteResponse> {
  const headers = await buildAuthHeaders()
  const response = await apiClient.post<ExplorationQuoteResponse>(
    `/explorations/${explorationId}/quote`,
    undefined,
    { headers },
  )
  return response.data
}

export async function generateExploration(
  explorationId: string,
  idempotencyKey: string,
): Promise<ExplorationGenerateResponse> {
  const authHeaders = await buildAuthHeaders()
  const headers = { 'Idempotency-Key': idempotencyKey, ...(authHeaders ?? {}) }
  const response = await apiClient.post<ExplorationGenerateResponse>(
    `/explorations/${explorationId}/generate`,
    {},
    { headers },
  )
  return response.data
}

async function buildAuthHeaders(): Promise<Record<string, string> | undefined> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) return undefined
  return { Authorization: `Bearer ${token}` }
}
