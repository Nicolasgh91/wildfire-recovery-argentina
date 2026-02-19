import { describe, expect, it } from 'vitest'
import { HOME_PATH, LOGIN_PATH, resolveReturnToPath, resolveRootDestination } from './routing'

describe('resolveRootDestination', () => {
  it('returns /home for authenticated users', () => {
    expect(resolveRootDestination('authenticated')).toBe(HOME_PATH)
  })

  it('returns /login for unauthenticated users', () => {
    expect(resolveRootDestination('unauthenticated')).toBe(LOGIN_PATH)
  })

  it('returns null while auth status is loading', () => {
    expect(resolveRootDestination('loading')).toBeNull()
  })

  it('falls back to /login for unexpected auth states', () => {
    expect(resolveRootDestination('unexpected')).toBe(LOGIN_PATH)
    expect(resolveRootDestination(undefined)).toBe(LOGIN_PATH)
    expect(resolveRootDestination(null)).toBe(LOGIN_PATH)
  })
})

describe('resolveReturnToPath', () => {
  it('keeps a valid returnTo path', () => {
    expect(resolveReturnToPath('/map')).toBe('/map')
  })

  it('returns /home when returnTo is missing', () => {
    expect(resolveReturnToPath(undefined)).toBe(HOME_PATH)
    expect(resolveReturnToPath(null)).toBe(HOME_PATH)
  })

  it('returns /home when returnTo is empty or whitespace', () => {
    expect(resolveReturnToPath('')).toBe(HOME_PATH)
    expect(resolveReturnToPath('   ')).toBe(HOME_PATH)
  })

  it('supports custom fallback path', () => {
    expect(resolveReturnToPath('', '/dashboard')).toBe('/dashboard')
  })
})
