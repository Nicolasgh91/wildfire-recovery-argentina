export const IDLE_ACTIVITY_STORAGE_KEY = 'forestguard_lastActivityAt'

export function touchIdleActivity(timestamp = Date.now()) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(IDLE_ACTIVITY_STORAGE_KEY, String(timestamp))
  } catch {
    // Ignore storage access failures (private mode, quota, etc.)
  }
}

export function clearIdleActivity() {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.removeItem(IDLE_ACTIVITY_STORAGE_KEY)
  } catch {
    // Ignore storage access failures (private mode, quota, etc.)
  }
}
