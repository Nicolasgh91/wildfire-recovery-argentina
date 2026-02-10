import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useExportMutation } from '@/hooks/mutations/useExportMutation'

const exportFiresMock = vi.fn()

vi.mock('@/services/endpoints/fires', () => ({
  exportFires: (...args: unknown[]) => exportFiresMock(...args),
}))

describe('useExportMutation', () => {
  const originalCreateElement = document.createElement.bind(document)

  beforeEach(() => {
    exportFiresMock.mockReset()
  })

  afterEach(() => {
    document.createElement = originalCreateElement
  })

  it('downloads blob responses', async () => {
    const blob = new Blob(['test'], { type: 'text/csv' })
    exportFiresMock.mockResolvedValue(blob)

    const createObjectURL = vi.fn(() => 'blob:mock')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(window, 'URL', {
      value: { createObjectURL, revokeObjectURL },
      writable: true,
    })

    const anchor = originalCreateElement('a')
    const click = vi.fn()
    const remove = vi.fn()
    anchor.click = click
    anchor.remove = remove

    const createElementSpy = vi
      .spyOn(document, 'createElement')
      .mockImplementation((tagName: string) => {
        if (tagName.toLowerCase() === 'a') return anchor
        return originalCreateElement(tagName)
      })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useExportMutation('incendios_historicos'), {
      wrapper,
    })

    await waitFor(async () => {
      await result.current.mutateAsync({ status_scope: 'historical' })
    })

    expect(exportFiresMock).toHaveBeenCalled()
    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(click).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalled()

    createElementSpy.mockRestore()
  })
})
