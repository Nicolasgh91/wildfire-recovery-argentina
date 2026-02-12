import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { useCreateCheckout } from '@/hooks/mutations/useCreateCheckout'

interface PaymentButtonProps {
  purpose: 'report' | 'credits'
  targetEntityType?: string
  targetEntityId?: string
  creditsAmount?: number
  metadata?: Record<string, unknown>
  children: React.ReactNode
  className?: string
  disabled?: boolean
}

export function PaymentButton({
  purpose,
  targetEntityType,
  targetEntityId,
  creditsAmount,
  metadata,
  children,
  className,
  disabled,
}: PaymentButtonProps) {
  const { mutate: createCheckout, isPending } = useCreateCheckout()
  const { isAuthenticated, status } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const isDisabled = disabled || isPending

  const handleClick = () => {
    console.info('[PaymentButton] click', {
      purpose,
      creditsAmount,
      targetEntityId,
      disabled,
      isPending,
    })
    if (isPending) return
    if (status === 'loading') {
      return
    }
    if (!isAuthenticated) {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('auth:returnTo', window.location.pathname + window.location.search)
      }
      toast.error(t('authRequired'))
      navigate('/login')
      return
    }
    if (purpose === 'credits' && !creditsAmount) {
      toast.error('Ingresá una cantidad válida de créditos.')
      return
    }
    if (purpose === 'report' && !targetEntityId) {
      toast.error('Falta seleccionar el reporte a pagar.')
      return
    }
    if (disabled) {
      return
    }
    createCheckout({
      purpose,
      target_entity_type: targetEntityType,
      target_entity_id: targetEntityId,
      credits_amount: creditsAmount,
      metadata,
    })
  }

  return (
    <Button
      type="button"
      onClick={handleClick}
      aria-disabled={isDisabled}
      data-debug="payment-button"
      className={cn(
        'pointer-events-auto relative z-10',
        isDisabled ? 'cursor-not-allowed opacity-50' : '',
        className
      )}
    >
      {isPending ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Procesando...
        </>
      ) : (
        children
      )}
    </Button>
  )
}
