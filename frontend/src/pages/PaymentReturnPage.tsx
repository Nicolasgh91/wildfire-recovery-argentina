import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle, Clock, Loader2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { usePaymentStatus } from '@/hooks/queries/usePaymentStatus'
import { useAuth } from '@/context/AuthContext'
import { useI18n } from '@/context/LanguageContext'

const POLLING_TIMEOUT_MS = 5 * 60 * 1000

export default function PaymentReturnPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [timedOut, setTimedOut] = useState(false)
  const { status } = useAuth()
  const { t } = useI18n()

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
        <h1 className="mb-2 text-2xl font-bold">{t('paymentLoadingSession')}</h1>
        <p className="text-gray-600">{t('paymentRestoringSession')}</p>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentSessionRequired')}</h1>
        <p className="mb-6 text-gray-600">
          {t('paymentLoginToVerify')}
        </p>
        <Button
          onClick={() => {
            sessionStorage.setItem('auth:returnTo', window.location.pathname + window.location.search)
            navigate('/login')
          }}
        >
          {t('paymentGoToLogin')}
        </Button>
      </div>
    )
  }

  if (!paymentRequestId) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentNotFound')}</h1>
        <p className="mb-6 text-gray-600">
          {t('paymentIdentifyError')}
        </p>
        <Button onClick={() => navigate('/credits')}>{t('paymentGoToCredits')}</Button>
      </div>
    )
  }

  if (timedOut) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <Clock className="mb-4 h-16 w-16 text-yellow-500" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentVerificationInProgress')}</h1>
        <p className="mb-6 text-gray-600">
          {t('paymentProcessingMessage')}
        </p>
        <Button onClick={() => navigate('/')}>{t('paymentGoToHome')}</Button>
      </div>
    )
  }

  if (isLoading || payment?.status === 'pending') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <Loader2 className="mb-4 h-16 w-16 animate-spin text-primary" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentVerifying')}</h1>
        <p className="text-gray-600">{t('paymentPleaseWait')}</p>
      </div>
    )
  }

  if (payment?.status === 'approved') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentSuccessful')}</h1>
        <p className="mb-6 text-gray-600">{t('paymentCreditedMessage')}</p>
        <Button onClick={() => navigate('/credits')}>{t('paymentContinue')}</Button>
      </div>
    )
  }

  if (payment?.status === 'rejected') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-4 text-center">
        <XCircle className="mb-4 h-16 w-16 text-red-500" />
        <h1 className="mb-2 text-2xl font-bold">{t('paymentRejected')}</h1>
        <p className="mb-6 text-gray-600">
          {t('paymentRejectedMessage')}
        </p>
        <Button onClick={() => navigate('/credits')}>{t('paymentTryAgain')}</Button>
      </div>
    )
  }

  return null
}
