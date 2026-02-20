export const HOME_PATH = '/home' as const
export const LOGIN_PATH = '/login' as const
const AUTH_CALLBACK_PATH = '/auth/callback' as const
const AUTH_RETURN_TO_STORAGE_KEY = 'auth:returnTo' as const

export function resolveRootDestination(
  status: string | null | undefined,
): typeof HOME_PATH | typeof LOGIN_PATH | null {
  if (status === 'loading') return null
  if (status === 'authenticated') return HOME_PATH
  return LOGIN_PATH
}

export function resolveReturnToPath(
  returnTo: string | null | undefined,
  fallback: string = HOME_PATH,
): string {
  const normalized = normalizeAuthPath(returnTo)
  return normalized ?? fallback
}

function normalizeAuthPath(rawPath: string | null | undefined): string | null {
  if (!rawPath) return null
  const trimmed = rawPath.trim()
  if (!trimmed) return null

  try {
    const baseOrigin = typeof window !== 'undefined' ? window.location.origin : 'https://localhost'
    const parsed = new URL(trimmed, baseOrigin)
    if (typeof window !== 'undefined' && parsed.origin !== window.location.origin) return null

    const normalizedPath = `${parsed.pathname}${parsed.search}${parsed.hash}`
    if (!normalizedPath.startsWith('/')) return null
    if (isAuthLoopPath(normalizedPath)) return null

    return normalizedPath
  } catch {
    return null
  }
}

function isAuthLoopPath(path: string): boolean {
  return (
    path === LOGIN_PATH ||
    path.startsWith(`${LOGIN_PATH}?`) ||
    path.startsWith(`${LOGIN_PATH}#`) ||
    path === AUTH_CALLBACK_PATH ||
    path.startsWith(`${AUTH_CALLBACK_PATH}?`) ||
    path.startsWith(`${AUTH_CALLBACK_PATH}#`)
  )
}

export function setAuthReturnTo(path: string | null | undefined) {
  if (typeof window === 'undefined') return

  const normalized = resolveReturnToPath(path, '')
  if (!normalized) {
    sessionStorage.removeItem(AUTH_RETURN_TO_STORAGE_KEY)
    return
  }

  sessionStorage.setItem(AUTH_RETURN_TO_STORAGE_KEY, normalized)
}

export function consumeAuthReturnTo(fallback: string = HOME_PATH): string {
  if (typeof window === 'undefined') return fallback

  const stored = sessionStorage.getItem(AUTH_RETURN_TO_STORAGE_KEY)
  sessionStorage.removeItem(AUTH_RETURN_TO_STORAGE_KEY)
  return resolveReturnToPath(stored, fallback)
}

export function clearAuthReturnTo() {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem(AUTH_RETURN_TO_STORAGE_KEY)
}
