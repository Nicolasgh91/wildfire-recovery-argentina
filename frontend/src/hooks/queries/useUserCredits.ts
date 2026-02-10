/**
 * @file useUserCredits.ts
 * @description Hook para obtener el saldo de créditos del usuario.
 */

import { useQuery } from '@tanstack/react-query'
import { getUserCredits } from '@/services/endpoints/credits'
import type { UserCredits } from '@/types/credits'

const FALLBACK_BALANCE = Number(import.meta.env.VITE_CREDITS_BALANCE || 0)

export function useUserCredits() {
  return useQuery<UserCredits>({
    queryKey: ['credits', 'balance'],
    queryFn: async () => {
      try {
        const data = await getUserCredits()
        return { ...data, source: 'api' }
      } catch {
        return {
          balance: FALLBACK_BALANCE,
          last_updated: null,
          source: 'fallback',
        }
      }
    },
    staleTime: 60 * 1000,
  })
}
