/**
 * @file usePaymentPricing.ts
 * @description Hook para obtener precios de creditos en ARS.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

export interface CreditPackagePricing {
  credits: number
  price_usd: number
  price_ars: number
}

export interface PaymentPricingResponse {
  currency: 'ARS'
  exchange_rate: number
  fetched_at: string
  source: string
  credit_packages: CreditPackagePricing[]
  report_price_usd: number
  report_price_ars: number
}

export function usePaymentPricing() {
  return useQuery<PaymentPricingResponse>({
    queryKey: ['payments', 'pricing'],
    queryFn: async () => {
      const response = await apiClient.get<PaymentPricingResponse>('/payments/pricing')
      return response.data
    },
  })
}
