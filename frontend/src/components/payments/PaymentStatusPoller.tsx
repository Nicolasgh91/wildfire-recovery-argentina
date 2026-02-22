import { useEffect } from 'react'
import { usePaymentStatus } from '@/hooks/queries/usePaymentStatus'

interface PaymentStatusPollerProps {
  paymentRequestId: string
  onStatusChange?: (status: string) => void
}

export function PaymentStatusPoller({ paymentRequestId, onStatusChange }: PaymentStatusPollerProps) {
  const { data } = usePaymentStatus(paymentRequestId, {
    enabled: !!paymentRequestId,
    refetchInterval: 3000,
  })

  useEffect(() => {
    if (data?.status) {
      onStatusChange?.(data.status)
    }
  }, [data?.status, onStatusChange])

  if (!data) return null

  return (
    <div className="text-sm text-muted-foreground">
      Estado del pago: <span className="font-semibold text-foreground">{data.status}</span>
    </div>
  )
}
