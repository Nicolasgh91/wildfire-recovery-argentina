/**
 * @file api.ts
 * @description Centralized HTTP client with auth/error interceptors.
 */

import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { toast } from 'sonner'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY
const API_KEY = import.meta.env.VITE_API_KEY || SUPABASE_ANON_KEY
const USE_SUPABASE_JWT = import.meta.env.VITE_USE_SUPABASE_JWT === 'true'
const DEFAULT_TIMEOUT = 30000
const MAX_RETRIES = 3
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

// Log environment configuration for debugging (dev only)
if (import.meta.env.DEV) {
  console.log('🔧 API Configuration:', {
    API_BASE_URL,
    SUPABASE_URL: SUPABASE_URL ? '[SET]' : '[NOT SET]',
    SUPABASE_ANON_KEY: SUPABASE_ANON_KEY ? '[SET]' : '[NOT SET]',
    API_KEY: API_KEY ? '[SET]' : '[NOT SET]',
    USE_SUPABASE_JWT,
    DEFAULT_TIMEOUT,
    NODE_ENV: import.meta.env.MODE
  })
}

type HeaderBag = InternalAxiosRequestConfig['headers']

let cachedAuthToken: string | null = null

function getHeaderValue(headers: HeaderBag, key: string): string | undefined {
  if (!headers) return undefined
  if (typeof (headers as { get?: (name: string) => string | undefined }).get === 'function') {
    const getter = (headers as { get: (name: string) => string | undefined }).get
    return getter.call(headers, key) ?? getter.call(headers, key.toLowerCase())
  }
  const record = headers as Record<string, string | undefined>
  return record[key] ?? record[key.toLowerCase()] ?? record[key.toUpperCase()]
}

function setHeaderValue(headers: HeaderBag, key: string, value: string) {
  if (!headers) return
  const setter = (headers as { set?: (name: string, value: string) => void }).set
  if (typeof setter === 'function') {
    setter.call(headers, key, value)
  } else {
    ; (headers as Record<string, string>)[key] = value
  }
}

function removeHeaderValue(headers: HeaderBag, key: string) {
  if (!headers) return
  const remover = (headers as { delete?: (name: string) => void }).delete
  if (typeof remover === 'function') {
    remover.call(headers, key)
  } else {
    delete (headers as Record<string, string>)[key]
  }
}

export function getAuthToken(): string | null {
  if (cachedAuthToken) return cachedAuthToken
  if (!SUPABASE_URL) return null

  try {
    const url = new URL(SUPABASE_URL)
    const projectRef = url.hostname.split('.')[0]
    const storageKey = `sb-${projectRef}-auth-token`
    const sessionStr = localStorage.getItem(storageKey)
    if (!sessionStr) return null
    const token = JSON.parse(sessionStr)?.access_token || null
    if (token) {
      cachedAuthToken = token
    }
    return token
  } catch {
    // ignore
  }
  return null
}

export function setAuthToken(token: string | null) {
  cachedAuthToken = token
}

export function requestInterceptor(config: InternalAxiosRequestConfig) {
  if (import.meta.env.DEV) {
    console.log('🔍 Axios Request Interceptor:', {
      method: config.method,
      url: config.url,
      baseURL: config.baseURL,
      hasData: !!config.data,
      dataType: config.data instanceof FormData ? 'FormData' : typeof config.data,
      headers: config.headers
    })
  }

  const headers = config.headers ?? {}

  if (API_KEY) {
    setHeaderValue(headers, 'X-API-Key', API_KEY)
  }

  const token = getAuthToken()
  if (token) {
    setHeaderValue(headers, 'Authorization', `Bearer ${token}`)
  }

  if (config.data instanceof FormData) {
    removeHeaderValue(headers, 'Content-Type')
  } else if (!getHeaderValue(headers, 'Content-Type')) {
    setHeaderValue(headers, 'Content-Type', 'application/json')
  }

  config.headers = headers
  if (import.meta.env.DEV) {
    console.log('✅ Request prepared:', {
      method: config.method,
      url: config.url,
      hasAuth: !!token,
      hasApiKey: !!API_KEY,
      contentType: getHeaderValue(headers, 'Content-Type')
    })
  }

  return config
}

function redirectToLogin() {
  if (typeof window === 'undefined') return
  const location = globalThis.location
  if (location && typeof location.assign === 'function') {
    location.assign('/login')
    return
  }
  if (location) {
    location.href = '/login'
  }
}

function shouldSkipAuthRedirect(config: InternalAxiosRequestConfig | undefined): boolean {
  if (!config) return false
  if ((config as { skipAuthRedirect?: boolean }).skipAuthRedirect) return true
  return getHeaderValue(config.headers, 'X-Skip-Auth-Redirect') === 'true'
}

export function handleHttpError(
  error: AxiosError,
  options?: { skipAuthRedirect?: boolean; hasAuthHeader?: boolean },
) {
  const status = error.response?.status

  switch (status) {
    case 401:
      if (options?.skipAuthRedirect || !USE_SUPABASE_JWT) return
      if (options?.hasAuthHeader === false) return
      toast.error('Session expired')
      redirectToLogin()
      break
    case 403:
      toast.error('Access denied')
      break
    case 422:
      toast.error('Invalid data')
      break
    case 429:
      toast.error('Too many requests')
      break
    default:
      if (status && status >= 500) {
        toast.error('Server error')
      } else if (!error.response) {
        toast.error('Connection error')
      }
  }
}

export async function responseErrorInterceptor(error: AxiosError) {
  if (import.meta.env.DEV) {
    console.error('🚨 Axios Response Error Interceptor:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      statusText: error.response?.statusText,
      url: error.config?.url,
      method: error.config?.method,
      responseData: error.response?.data
    })
  }

  const config = error.config as
    | (InternalAxiosRequestConfig & { _retryCount?: number; _authRetried?: boolean })
    | undefined

  const skipAuthRedirect =
    (config as { skipAuthRedirect?: boolean } | undefined)?.skipAuthRedirect ||
    shouldSkipAuthRedirect(config)
  const hasAuthHeader = Boolean(getHeaderValue(config?.headers || ({} as any), 'Authorization'))
  const status = error.response?.status

  if (
    status === 401 &&
    config &&
    !config._authRetried &&
    USE_SUPABASE_JWT &&
    !skipAuthRedirect &&
    hasAuthHeader
  ) {
    config._authRetried = true
    try {
      const { supabase } = await import('@/lib/supabase')
      const { data, error: refreshError } = await supabase.auth.refreshSession()
      const refreshedToken = data?.session?.access_token
      if (refreshError || !refreshedToken) {
        throw refreshError || new Error('No refreshed session')
      }
      setAuthToken(refreshedToken)
      setHeaderValue(config.headers, 'Authorization', `Bearer ${refreshedToken}`)
      return apiClient.request(config)
    } catch {
      // fall through to existing auth handling
    }
  }

  // PERF-007: Only retry idempotent methods to avoid duplicate mutations
  const IDEMPOTENT_METHODS = ['get', 'head', 'options']
  const method = (config?.method || '').toLowerCase()
  if (config && (config._retryCount || 0) < MAX_RETRIES && IDEMPOTENT_METHODS.includes(method)) {
    if (!error.response || RETRYABLE_STATUS_CODES.includes(error.response.status)) {
      config._retryCount = (config._retryCount || 0) + 1
      const baseDelay = 1000 * config._retryCount!
      const jitter = Math.random() * 500
      await new Promise((resolve) => setTimeout(resolve, baseDelay + jitter))
      return apiClient.request(config)
    }
  }

  handleHttpError(error, { skipAuthRedirect, hasAuthHeader })
  return Promise.reject(error)
}

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
  })

  client.interceptors.request.use(requestInterceptor)
  client.interceptors.response.use(
    (response) => {
      if (import.meta.env.DEV) {
        console.log('✅ Axios Response Success:', {
          status: response.status,
          statusText: response.statusText,
          url: response.config.url,
          method: response.config.method,
          hasData: !!response.data
        })
      }
      return response
    },
    responseErrorInterceptor
  )

  return client
}

export const apiClient = createApiClient()
