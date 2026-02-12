import * as Sentry from '@sentry/react'

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN

export function initSentry() {
  const isProd = import.meta.env.PROD
  const hasValidDsn = SENTRY_DSN && SENTRY_DSN.startsWith('https://')
  if (!isProd || !hasValidDsn) return

  Sentry.init({
    dsn: SENTRY_DSN,
    tracesSampleRate: 0,
  })
}
