import { describe, expect, it } from 'vitest'
import {
  HOME_PATH,
  LOGIN_PATH,
  clearAuthReturnTo,
  consumeAuthReturnTo,
  resolveReturnToPath,
  resolveRootDestination,
  setAuthReturnTo,
} from './routing'

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

  it('rejects external URLs', () => {
    expect(resolveReturnToPath('https://example.com/phishing')).toBe(HOME_PATH)
  })

  it('rejects login and auth callback paths to avoid loops', () => {
    expect(resolveReturnToPath('/login')).toBe(HOME_PATH)
    expect(resolveReturnToPath('/auth/callback')).toBe(HOME_PATH)
  })
})

describe('auth:returnTo helpers', () => {
  it('stores only valid auth return paths', () => {
    setAuthReturnTo('/map?layer=active')
    expect(sessionStorage.getItem('auth:returnTo')).toBe('/map?layer=active')

    setAuthReturnTo('/login')
    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('consumes and clears stored value atomically', () => {
    sessionStorage.setItem('auth:returnTo', '/exploracion')
    expect(consumeAuthReturnTo()).toBe('/exploracion')
    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })

  it('clearAuthReturnTo removes value', () => {
    sessionStorage.setItem('auth:returnTo', '/map')
    clearAuthReturnTo()
    expect(sessionStorage.getItem('auth:returnTo')).toBeNull()
  })
})
