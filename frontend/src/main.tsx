import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import 'leaflet/dist/leaflet.css'
import './index.css'
import App from './App.tsx'
import { Toaster } from '@/components/ui/toaster'
import { queryClient } from '@/lib/queryClient'
import { initSentry } from '@/lib/sentry'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'

initSentry()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <App />
        <Toaster />
        <ReactQueryDevtools initialIsOpen={false} />
      </ErrorBoundary>
    </QueryClientProvider>
  </StrictMode>,
)
