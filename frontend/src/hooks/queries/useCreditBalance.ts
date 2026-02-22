/**
 * @file useCreditBalance.ts
 * @description Hook para obtener el saldo de créditos del usuario.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuth } from '@/context/AuthContext'

interface CreditBalanceResponse {
  balance: number
  last_updated: string
}

export function useCreditBalance() {
  const { isAuthenticated } = useAuth()

  return useQuery<CreditBalanceResponse>({
    queryKey: ['credits', 'balance'],
    queryFn: async () => {
      const response = await apiClient.get<CreditBalanceResponse>(
        '/payments/credits/balance',
      )
      return response.data
    },
    enabled: isAuthenticated,
  })
}
