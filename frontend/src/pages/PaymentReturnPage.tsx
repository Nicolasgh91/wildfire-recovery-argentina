import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle, Clock, Loader2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePaymentStatus } from '@/hooks/queries/usePaymentStatus'
import { useAuth } from '@/context/AuthContext'

const POLLING_TIMEOUT_MS = 5 * 60 * 1000

export default function PaymentReturnPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [timedOut, setTimedOut] = useState(false)
  const { status } = useAuth()

  const paymentRequestId = useMemo(() => {
    const fromQuery = searchParams.get('payment_request_id')
    if (fromQuery) return fromQuery
    return sessionStorage.getItem('payment:requestId') || ''
  }, [searchParams])

  useEffect(() => {
    const fromQuery = searchParams.get('payment_request_id')
    if (fromQuery) {
      sessionStorage.setItem('payment:requestId', fromQuery)
    }
  }, [searchParams])

  const canFetch = status === 'authenticated' && !!paymentRequestId && !timedOut
  const { data: payment, isLoading } = usePaymentStatus(paymentRequestId, {
    enabled: canFetch,
    refetchInterval: 3000,
    skipAuthRedirect: true,
  })

  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), POLLING_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [])

  if (status === 'loading') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <Loader2 className="mb-4 h-16 w-16 animate-spin text-primary" />
        <h1 className="mb-2 text-2xl font-bold">Cargando sesion...</h1>
        <p className="text-gray-600">Estamos restaurando tu sesion antes de verificar el pago.</p>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">Sesion requerida</h1>
        <p className="mb-6 text-gray-600">
          Inicia sesion para verificar el estado del pago.
        </p>
        <Button
          onClick={() => {
            sessionStorage.setItem('auth:returnTo', window.location.pathname + window.location.search)
            navigate('/login')
          }}
        >
          Ir a login
        </Button>
      </div>
    )
  }

  if (!paymentRequestId) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">Pago no encontrado</h1>
        <p className="mb-6 text-gray-600">
          No pudimos identificar el pago. Volve a intentar desde Creditos.
        </p>
        <Button onClick={() => navigate('/credits')}>Ir a Creditos</Button>
      </div>
    )
  }

  if (timedOut) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <Clock className="mb-4 h-16 w-16 text-yellow-500" />
        <h1 className="mb-2 text-2xl font-bold">Verificación en proceso</h1>
        <p className="mb-6 text-gray-600">
          Tu pago está siendo procesado. Recibirás un email de confirmación cuando se acredite.
        </p>
        <Button onClick={() => navigate('/')}>Volver al inicio</Button>
      </div>
    )
  }

  if (isLoading || payment?.status === 'pending') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <Loader2 className="mb-4 h-16 w-16 animate-spin text-primary" />
        <h1 className="mb-2 text-2xl font-bold">Verificando pago...</h1>
        <p className="text-gray-600">Por favor espera mientras confirmamos tu pago.</p>
      </div>
    )
  }

  if (payment?.status === 'approved') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
        <h1 className="mb-2 text-2xl font-bold">¡Pago exitoso!</h1>
        <p className="mb-6 text-gray-600">Tus créditos han sido acreditados a tu cuenta.</p>
        <Button onClick={() => navigate('/credits')}>Continuar</Button>
      </div>
    )
  }

  if (payment?.status === 'rejected') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">Pago rechazado</h1>
        <p className="mb-6 text-gray-600">
          No pudimos procesar tu pago. Por favor intenta nuevamente.
        </p>
        <Button onClick={() => navigate('/credits')}>Intentar de nuevo</Button>
      </div>
    )
  }

  return null
}
