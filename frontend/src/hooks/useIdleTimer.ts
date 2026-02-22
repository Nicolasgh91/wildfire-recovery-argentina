import { useCallback, useEffect, useRef } from 'react'
import { IDLE_ACTIVITY_STORAGE_KEY, touchIdleActivity } from '@/lib/idleActivity'

type IdleTimerOptions = {
  enabled?: boolean
  onIdle: () => void | Promise<void>
  timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 30 * 60 * 1000
const WRITE_THROTTLE_MS = 60 * 1000

export function useIdleTimer({
  enabled = true,
  onIdle,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}: IdleTimerOptions) {
  const idleTimeoutRef = useRef<number | null>(null)
  const lastActivityRef = useRef<number>(Date.now())
  const lastWriteRef = useRef<number>(0)
  const idleTriggeredRef = useRef(false)

  const clearTimer = useCallback(() => {
    if (idleTimeoutRef.current !== null) {
      window.clearTimeout(idleTimeoutRef.current)
      idleTimeoutRef.current = null
    }
  }, [])

  const triggerIdle = useCallback(() => {
    if (idleTriggeredRef.current) return
    idleTriggeredRef.current = true
    Promise.resolve(onIdle()).catch(() => undefined)
  }, [onIdle])

  const scheduleTimer = useCallback(() => {
    clearTimer()
    idleTimeoutRef.current = window.setTimeout(() => {
      const elapsed = Date.now() - lastActivityRef.current
      if (elapsed >= timeoutMs) {
        triggerIdle()
      } else {
        scheduleTimer()
      }
    }, timeoutMs)
  }, [clearTimer, timeoutMs, triggerIdle])

  const writeLastActivity = useCallback((timestamp: number) => {
    if (timestamp - lastWriteRef.current < WRITE_THROTTLE_MS) return
    lastWriteRef.current = timestamp
    touchIdleActivity(timestamp)
  }, [])

  const recordActivity = useCallback(() => {
    if (!enabled) return
    const now = Date.now()
    lastActivityRef.current = now
    idleTriggeredRef.current = false
    writeLastActivity(now)
    scheduleTimer()
  }, [enabled, scheduleTimer, writeLastActivity])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (!enabled) {
      clearTimer()
      return
    }

    const now = Date.now()
    lastActivityRef.current = now
    idleTriggeredRef.current = false

    try {
      const stored = localStorage.getItem(IDLE_ACTIVITY_STORAGE_KEY)
      if (stored) {
        const parsed = Number(stored)
        if (Number.isFinite(parsed)) {
          lastActivityRef.current = parsed
          if (now - parsed >= timeoutMs) {
            triggerIdle()
          }
        }
      }
    } catch {
      // ignore storage errors
    }

    scheduleTimer()

    const events = ['mousemove', 'keydown', 'scroll', 'touchstart', 'click']
    const listener = () => recordActivity()
    events.forEach((eventName) => {
      window.addEventListener(eventName, listener, { passive: true })
    })

    const storageListener = (event: StorageEvent) => {
      if (event.key !== IDLE_ACTIVITY_STORAGE_KEY || !event.newValue) return
      const parsed = Number(event.newValue)
      if (!Number.isFinite(parsed)) return
      lastActivityRef.current = parsed
      idleTriggeredRef.current = false
      if (Date.now() - parsed >= timeoutMs) {
        triggerIdle()
      } else {
        scheduleTimer()
      }
    }

    window.addEventListener('storage', storageListener)

    return () => {
      clearTimer()
      events.forEach((eventName) => {
        window.removeEventListener(eventName, listener)
      })
      window.removeEventListener('storage', storageListener)
    }
  }, [clearTimer, enabled, recordActivity, scheduleTimer, timeoutMs, triggerIdle])
}
