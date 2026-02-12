/**
 * Feature flags for ForestGuard MVP.
 *
 * Reads from VITE_FF_* with fallback to legacy VITE_FEATURE_*.
 */

function resolveFlagKey(flag: string) {
  return flag.trim().toUpperCase().replace(/[^A-Z0-9_]/g, '_')
}

export function isFeatureEnabled(flag: string): boolean {
  const key = resolveFlagKey(flag)
  const nextValue = (import.meta.env as Record<string, string | undefined>)[
    `VITE_FF_${key}`
  ]
  const legacyValue = (import.meta.env as Record<string, string | undefined>)[
    `VITE_FEATURE_${key}`
  ]
  const value = nextValue ?? legacyValue
  return value === 'true'
}
