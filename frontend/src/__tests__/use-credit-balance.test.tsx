import type { ReactNode } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { useCreditBalance } from '@/hooks/queries/useCreditBalance'

const apiGetMock = vi.fn()
let isAuthenticated = false

vi.mock('@/services/api', () => ({
  apiClient: {
    get: (...args: unknown[]) => apiGetMock(...args),
  },
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    status: isAuthenticated ? 'authenticated' : 'unauthenticated',
    role: isAuthenticated ? 'user' : 'anonymous',
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signUpWithEmail: vi.fn(),
    signOut: vi.fn(),
    isAuthenticated,
  }),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useCreditBalance', () => {
  beforeEach(() => {
    apiGetMock.mockReset()
    isAuthenticated = false
  })

  it('does not request balance when user is unauthenticated', async () => {
    apiGetMock.mockResolvedValue({
      data: { balance: 0, last_updated: '2026-02-13T00:00:00Z' },
    })

    const { result } = renderHook(() => useCreditBalance(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle')
    })
    expect(apiGetMock).not.toHaveBeenCalled()
  })

  it('requests balance when user is authenticated', async () => {
    isAuthenticated = true
    apiGetMock.mockResolvedValue({
      data: { balance: 12, last_updated: '2026-02-13T00:00:00Z' },
    })

    const { result } = renderHook(() => useCreditBalance(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.data?.balance).toBe(12)
    })
    expect(apiGetMock).toHaveBeenCalledTimes(1)
    expect(apiGetMock).toHaveBeenCalledWith('/payments/credits/balance')
  })
})
