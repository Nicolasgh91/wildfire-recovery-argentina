import { describe, expect, it } from 'vitest'
import { runValidation } from '../../scripts/validate-build-env.mjs'

function createBaseEnv(overrides: Record<string, string> = {}) {
  return {
    NODE_ENV: 'production',
    VITE_SUPABASE_URL: 'https://qkmuwmxifbahmcydteuj.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'anon-key',
    VITE_API_BASE_URL: '/api/v1',
    ...overrides,
  }
}

describe('validate-build-env', () => {
  it('accepts a valid production auth redirect URL', () => {
    const env = createBaseEnv({
      VITE_AUTH_REDIRECT_URL: 'https://forestguard.freedynamicdns.org/auth/callback',
    })

    expect(() => runValidation(env)).not.toThrow()
  })

  it('rejects an invalid auth redirect URL', () => {
    const env = createBaseEnv({
      VITE_AUTH_REDIRECT_URL: 'not-a-url',
    })

    expect(() => runValidation(env)).toThrow(/VITE_AUTH_REDIRECT_URL is not a valid URL/i)
  })

  it('rejects auth redirect URLs that do not end in /auth/callback', () => {
    const env = createBaseEnv({
      VITE_AUTH_REDIRECT_URL: 'https://forestguard.freedynamicdns.org/login',
    })

    expect(() => runValidation(env)).toThrow(/must end in \/auth\/callback/i)
  })

  it('rejects localhost auth redirect in production builds', () => {
    const env = createBaseEnv({
      NODE_ENV: 'production',
      VITE_AUTH_REDIRECT_URL: 'http://localhost:5173/auth/callback',
    })

    expect(() => runValidation(env)).toThrow(/must not point to localhost/i)
  })

  it('accepts localhost auth redirect in development builds', () => {
    const env = createBaseEnv({
      NODE_ENV: 'development',
      VITE_AUTH_REDIRECT_URL: 'http://localhost:5173/auth/callback',
    })

    expect(() => runValidation(env)).not.toThrow()
  })

  it('rejects localhost auth redirect when CI mode is enabled', () => {
    const env = createBaseEnv({
      NODE_ENV: 'development',
      CI: 'true',
      VITE_AUTH_REDIRECT_URL: 'http://localhost:5173/auth/callback',
    })

    expect(() => runValidation(env)).toThrow(/must not point to localhost/i)
  })
})
