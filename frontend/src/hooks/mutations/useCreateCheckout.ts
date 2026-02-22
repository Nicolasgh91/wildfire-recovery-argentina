/**
 * @file useCreateCheckout.ts
 * @description Hook para crear un checkout de MercadoPago.
 */

import { useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'

interface CreateCheckoutRequest {
  purpose: 'report' | 'credits'
  target_entity_type?: string
  target_entity_id?: string
  credits_amount?: number
  metadata?: Record<string, unknown>
  client_platform?: 'web' | 'android'
}

interface CreateCheckoutResponse {
  payment_request_id: string
  checkout_url: string
  external_reference: string
  amount_usd: number
  amount_ars: number
  exchange_rate: number
  expires_at: string
}

export function useCreateCheckout() {
  return useMutation<CreateCheckoutResponse, Error, CreateCheckoutRequest>({
    mutationFn: async (data) => {
      const clientPlatform =
        (import.meta.env.VITE_CLIENT_PLATFORM as 'web' | 'android' | undefined) || 'web'
      console.info('[useCreateCheckout] mutationFn', data)
      const response = await apiClient.post<CreateCheckoutResponse>(
        '/payments/checkout',
        { ...data, client_platform: clientPlatform },
      )
      console.info('[useCreateCheckout] response', response.status)
      return response.data
    },
    onSuccess: (data) => {
      console.info('[useCreateCheckout] onSuccess', data)
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('payment:returnTo', window.location.pathname + window.location.search)
        sessionStorage.setItem('payment:requestId', data.payment_request_id)
        window.location.href = data.checkout_url
      }
    },
    onError: (error) => {
      console.error('[useCreateCheckout] onError', error)
      if (error instanceof AxiosError) {
        const message =
          (error.response?.data as { detail?: string } | undefined)?.detail ||
          error.message
        toast.error(message || 'No se pudo iniciar el pago.')
        return
      }
      toast.error(error.message || 'No se pudo iniciar el pago.')
    },
  })
}
