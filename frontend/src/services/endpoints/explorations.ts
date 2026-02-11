/**
 * @file explorations.ts
 * @description Exploration endpoints.
 */

import { apiClient } from '../api'
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
  const response = await apiClient.post<ExplorationResponse>('/explorations/', payload, {
    headers: { 'X-Skip-Auth-Redirect': 'true' },
    skipAuthRedirect: true,
  } as any)
  return response.data
}

export async function updateExploration(
  explorationId: string,
  payload: ExplorationUpdateRequest,
): Promise<ExplorationResponse> {
  const response = await apiClient.patch<ExplorationResponse>(
    `/explorations/${explorationId}`,
    payload,
    { headers: { 'X-Skip-Auth-Redirect': 'true' }, skipAuthRedirect: true } as any,
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
    { headers: { 'X-Skip-Auth-Redirect': 'true' }, skipAuthRedirect: true } as any,
  )
  return response.data
}

export async function deleteExplorationItem(
  explorationId: string,
  itemId: string,
): Promise<void> {
  await apiClient.delete(`/explorations/${explorationId}/items/${itemId}`, {
    headers: { 'X-Skip-Auth-Redirect': 'true' },
    skipAuthRedirect: true,
  } as any)
}

export async function getExplorationQuote(
  explorationId: string,
): Promise<ExplorationQuoteResponse> {
  const response = await apiClient.post<ExplorationQuoteResponse>(
    `/explorations/${explorationId}/quote`,
    undefined,
    { headers: { 'X-Skip-Auth-Redirect': 'true' }, skipAuthRedirect: true } as any,
  )
  return response.data
}

export async function generateExploration(
  explorationId: string,
  idempotencyKey: string,
): Promise<ExplorationGenerateResponse> {
  const headers = {
    'Idempotency-Key': idempotencyKey,
    'X-Skip-Auth-Redirect': 'true',
  }
  const response = await apiClient.post<ExplorationGenerateResponse>(
    `/explorations/${explorationId}/generate`,
    {},
    { headers, skipAuthRedirect: true } as any,
  )
  return response.data
}
