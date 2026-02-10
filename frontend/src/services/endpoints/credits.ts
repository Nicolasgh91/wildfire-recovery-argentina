/**
 * @file credits.ts
 * @description Credit balance endpoints.
 */

import { apiClient } from '../api'
import type { UserCredits } from '@/types/credits'

export async function getUserCredits(): Promise<UserCredits> {
  const response = await apiClient.get<UserCredits>('/payments/credits/balance', {
    headers: { 'X-Skip-Auth-Redirect': 'true' },
  })
  return response.data
}
