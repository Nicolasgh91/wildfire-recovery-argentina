import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import 'leaflet/dist/leaflet.css'
import './index.css'
import App from './App.tsx'
import { Toaster } from '@/components/ui/sonner'
import { Toaster as RadixToaster } from '@/components/ui/toaster'
import { queryClient } from '@/lib/queryClient'
import { ErrorBoundary } from '@/components/error/ErrorBoundary'

if (import.meta.env.PROD) {
  window.addEventListener('unhandledrejection', (event) => {
    console.error('[ForestGuard] Unhandled rejection:', event.reason)
  })
  window.addEventListener('error', (event) => {
    console.error('[ForestGuard] Global error:', event.error)
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <App />
        <Toaster />
        <RadixToaster />
        <ReactQueryDevtools initialIsOpen={false} />
      </ErrorBoundary>
    </QueryClientProvider>
  </StrictMode>,
)
