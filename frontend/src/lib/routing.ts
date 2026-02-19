export const HOME_PATH = '/home' as const
export const LOGIN_PATH = '/login' as const

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
  if (!returnTo) return fallback
  const normalized = returnTo.trim()
  if (normalized === '') return fallback
  return normalized
}
