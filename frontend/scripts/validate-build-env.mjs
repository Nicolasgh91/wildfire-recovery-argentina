#!/usr/bin/env node

const REQUIRED_KEYS = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY']
const OPTIONAL_DEFAULT_API_BASE_URL = '/api/v1'

function fail(message) {
  console.error(`[build-env] ${message}`)
  process.exit(1)
}

function getEnv(name, fallback = '') {
  const value = process.env[name]
  if (typeof value !== 'string') return fallback
  return value.trim()
}

function validateRequiredEnv() {
  const missing = REQUIRED_KEYS.filter((key) => getEnv(key) === '')
  if (missing.length > 0) {
    fail(`Missing required frontend build variables: ${missing.join(', ')}`)
  }
}

function validateApiBaseUrl() {
  const apiBaseUrl = getEnv('VITE_API_BASE_URL', OPTIONAL_DEFAULT_API_BASE_URL)
  if (/localhost|127\.0\.0\.1/i.test(apiBaseUrl)) {
    fail('VITE_API_BASE_URL must not point to localhost/127.0.0.1 in production builds.')
  }
}

function validateSupabaseUrl() {
  const supabaseUrl = getEnv('VITE_SUPABASE_URL')
  try {
    const parsed = new URL(supabaseUrl)
    if (!['https:', 'http:'].includes(parsed.protocol)) {
      fail('VITE_SUPABASE_URL must use http or https protocol.')
    }
  } catch (error) {
    fail(`VITE_SUPABASE_URL is not a valid URL: ${error.message}`)
  }
}

validateRequiredEnv()
validateApiBaseUrl()
validateSupabaseUrl()

console.log('[build-env] Frontend build environment validated.')
