import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { toast } from 'sonner'

vi.mock('sonner', () => {
  const toastMock = Object.assign(vi.fn(), { error: vi.fn() })
  return { toast: toastMock }
})

describe('ApiService', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    vi.stubEnv('VITE_API_BASE_URL', 'http://example.com/api/v1')
    vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
    vi.stubEnv('VITE_API_KEY', '')
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('injects X-API-Key and Authorization headers', async () => {
    vi.stubEnv('VITE_USE_SUPABASE_JWT', 'true')
    localStorage.setItem('sb-test-auth-token', JSON.stringify({ access_token: 'token' }))

    const { requestInterceptor } = await import('../services/api')
    const config = { headers: {} } as InternalAxiosRequestConfig

    const result = requestInterceptor(config)

    expect(result.headers['X-API-Key']).toBe('anon-key')
    expect(result.headers['Authorization']).toBe('Bearer token')
  })

  it('attaches Authorization when setAuthToken is used', async () => {
    const { requestInterceptor, setAuthToken } = await import('../services/api')
    const config = { headers: {} } as InternalAxiosRequestConfig

    setAuthToken('cached-token')
    const result = requestInterceptor(config)

    expect(result.headers['Authorization']).toBe('Bearer cached-token')
  })

  it('does not attach Authorization when no token is available', async () => {
    const { requestInterceptor } = await import('../services/api')
    const config = { headers: {} } as InternalAxiosRequestConfig

    const result = requestInterceptor(config)

    expect(result.headers['Authorization']).toBeUndefined()
  })

  it('removes content-type for FormData requests', async () => {
    const { requestInterceptor } = await import('../services/api')
    const config = {
      headers: { 'Content-Type': 'application/json' },
      data: new FormData(),
    } as InternalAxiosRequestConfig

    const result = requestInterceptor(config)

    expect(result.headers['Content-Type']).toBeUndefined()
  })

  it('retries on retryable errors', async () => {
    vi.useFakeTimers()
    const { apiClient, responseErrorInterceptor } = await import('../services/api')

    const config = { headers: {} } as InternalAxiosRequestConfig & { _retryCount?: number }
    const requestSpy = vi
      .spyOn(apiClient, 'request')
      .mockResolvedValue({ data: {} } as never)

    const error = new AxiosError(
      'Server error',
      'ERR_BAD_RESPONSE',
      config,
      {},
      { status: 500 } as never
    )

    const promise = responseErrorInterceptor(error)
    await vi.runAllTimersAsync()
    await promise

    expect(requestSpy).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('redirects to login on 401', async () => {
    vi.stubEnv('VITE_USE_SUPABASE_JWT', 'true')
    const { handleHttpError } = await import('../services/api')
    const assignSpy = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign: assignSpy })

    handleHttpError(
      new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 401,
      } as never)
    )

    expect(toast.error).toHaveBeenCalledWith('Session expired')
    expect(assignSpy).toHaveBeenCalledWith('/login')
  })

  it('skips auth redirect when X-Skip-Auth-Redirect is set', async () => {
    vi.stubEnv('VITE_USE_SUPABASE_JWT', 'true')
    const { responseErrorInterceptor } = await import('../services/api')
    const assignSpy = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign: assignSpy })

    const config = {
      headers: { 'X-Skip-Auth-Redirect': 'true' },
    } as InternalAxiosRequestConfig & { _retryCount?: number }

    const error = new AxiosError(
      'Unauthorized',
      'ERR_BAD_REQUEST',
      config,
      {},
      { status: 401 } as never
    )

    await expect(responseErrorInterceptor(error)).rejects.toBe(error)
    expect(toast.error).not.toHaveBeenCalledWith('Session expired')
    expect(assignSpy).not.toHaveBeenCalled()
  })
})
