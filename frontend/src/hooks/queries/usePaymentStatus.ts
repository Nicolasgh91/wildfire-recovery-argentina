/**
 * @file usePaymentStatus.ts
 * @description Hook para consultar estado de pagos.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

interface PaymentStatusResponse {
  id: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  purpose: string
  amount_usd: number
  amount_ars?: number
  created_at: string
  approved_at?: string
}

export function usePaymentStatus(
  paymentRequestId: string,
  options?: {
    enabled?: boolean
    refetchInterval?: number | false
    skipAuthRedirect?: boolean
  },
) {
  return useQuery<PaymentStatusResponse>({
    queryKey: ['payment', paymentRequestId],
    queryFn: async () => {
      const response = await apiClient.get<PaymentStatusResponse>(
        `/payments/${paymentRequestId}`,
        (options?.skipAuthRedirect ? { skipAuthRedirect: true } : undefined) as any,
      )
      return response.data
    },
    enabled: options?.enabled ?? !!paymentRequestId,
    refetchInterval: (data) => {
      if (data?.status === 'approved' || data?.status === 'rejected') {
        return false
      }
      return options?.refetchInterval ?? 3000
    },
  })
}
