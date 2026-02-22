#!/usr/bin/env node

import { pathToFileURL } from 'node:url'

const REQUIRED_KEYS = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY']
const OPTIONAL_DEFAULT_API_BASE_URL = '/api/v1'
const AUTH_CALLBACK_PATH = '/auth/callback'

export function getEnv(env, name, fallback = '') {
  const value = env?.[name]
  if (typeof value !== 'string') return fallback
  return value.trim()
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function isLocalHost(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1'
}

export function validateRequiredEnv(env = process.env) {
  const missing = REQUIRED_KEYS.filter((key) => getEnv(env, key) === '')
  assert(missing.length === 0, `Missing required frontend build variables: ${missing.join(', ')}`)
}

export function validateApiBaseUrl(env = process.env) {
  const apiBaseUrl = getEnv(env, 'VITE_API_BASE_URL', OPTIONAL_DEFAULT_API_BASE_URL)
  assert(
    !/localhost|127\.0\.0\.1/i.test(apiBaseUrl),
    'VITE_API_BASE_URL must not point to localhost/127.0.0.1 in production builds.',
  )
}

export function validateSupabaseUrl(env = process.env) {
  const supabaseUrl = getEnv(env, 'VITE_SUPABASE_URL')
  let parsed
  try {
    parsed = new URL(supabaseUrl)
  } catch (error) {
    throw new Error(`VITE_SUPABASE_URL is not a valid URL: ${error.message}`)
  }

  assert(['https:', 'http:'].includes(parsed.protocol), 'VITE_SUPABASE_URL must use http or https protocol.')
}

export function validateAuthRedirectUrl(env = process.env) {
  const rawRedirect = getEnv(env, 'VITE_AUTH_REDIRECT_URL')
  if (!rawRedirect) return

  let parsed
  try {
    parsed = new URL(rawRedirect)
  } catch (error) {
    throw new Error(`VITE_AUTH_REDIRECT_URL is not a valid URL: ${error.message}`)
  }

  assert(['https:', 'http:'].includes(parsed.protocol), 'VITE_AUTH_REDIRECT_URL must use http or https protocol.')
  assert(
    parsed.pathname === AUTH_CALLBACK_PATH,
    `VITE_AUTH_REDIRECT_URL must end in ${AUTH_CALLBACK_PATH}. Received path: ${parsed.pathname}`,
  )

  const nodeEnv = getEnv(env, 'NODE_ENV', '').toLowerCase()
  const ciMode = getEnv(env, 'CI', '').toLowerCase() === 'true'
  const isProductionBuild = nodeEnv === 'production' || ciMode
  assert(
    !isProductionBuild || !isLocalHost(parsed.hostname),
    'VITE_AUTH_REDIRECT_URL must not point to localhost/127.0.0.1 in production builds.',
  )
}

export function runValidation(env = process.env) {
  validateRequiredEnv(env)
  validateApiBaseUrl(env)
  validateSupabaseUrl(env)
  validateAuthRedirectUrl(env)
}

function fail(message) {
  console.error(`[build-env] ${message}`)
  process.exit(1)
}

const isDirectExecution = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href
if (isDirectExecution) {
  try {
    runValidation(process.env)
    console.log('[build-env] Frontend build environment validated.')
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error))
  }
}
