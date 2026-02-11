/**
 * @file auth.ts
 * @description Native authentication service for ForestGuard
 * Replaces Supabase auth with direct backend API calls
 */

import { apiClient } from '@/services/api'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential?: string }) => void
          }) => void
          prompt: () => void
        }
      }
    }
  }
}

/**
 * Derives the localStorage key for storing auth tokens
 * Matches the logic in services/api.ts getAuthToken()
 * Key format: sb-{projectRef}-auth-token where projectRef is extracted from VITE_SUPABASE_URL
 */
function getStorageKey(): string {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
  if (!supabaseUrl) {
    return 'sb-forestguard-auth-token' // fallback for dev without Supabase
  }

  try {
    const url = new URL(supabaseUrl)
    const projectRef = url.hostname.split('.')[0]
    return `sb-${projectRef}-auth-token`
  } catch {
    return 'sb-forestguard-auth-token'
  }
}

// Dynamic storage key - matches getAuthToken() in services/api.ts
const STORAGE_KEY = getStorageKey()

interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    email: string
    full_name: string | null
    dni: string | null
    role: string
    avatar_url: string | null
    created_at: string
    is_verified: boolean
  }
}

interface Session {
  access_token: string
  user: AuthResponse['user']
  expires_at: number
}

interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  avatar_url: string | null
}

interface RegisterPayload {
  email: string
  password: string
  full_name: string
  dni: string
}

export const nativeAuth = {
  /**
   * Sign in with email and password
   */
  async signInWithPassword(email: string, password: string): Promise<{ data: { session: Session | null }, error: Error | null }> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/login', {
        email,
        password,
      })

      // Store token in Supabase-compatible format
      const session: Session = {
        access_token: response.data.access_token,
        user: response.data.user,
        expires_at: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))

      return { data: { session }, error: null }
    } catch (error) {
      return { data: { session: null }, error: error as Error }
    }
  },

  /**
   * Sign in with Google OAuth
   */
  async signInWithOAuth(config: { provider: string; options?: { redirectTo?: string } }): Promise<{ data: { url?: string }, error: Error | null }> {
    if (config.provider !== 'google') {
      return { data: {}, error: new Error('Only Google OAuth is supported') }
    }

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) {
      return { data: {}, error: new Error('VITE_GOOGLE_CLIENT_ID is not configured') }
    }

    const google = window.google
    if (!google?.accounts?.id) {
      return { data: {}, error: new Error('Google Sign-In SDK is not loaded') }
    }

    return new Promise((resolve) => {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (!response.credential) {
            resolve({ data: {}, error: new Error('Google OAuth cancelled') })
            return
          }

          const result = await this.signInWithGoogleCredential(response.credential)
          if (result.error) {
            resolve({ data: {}, error: result.error })
            return
          }

          resolve({ data: {}, error: null })
        },
      })

      google.accounts.id.prompt()
    })
  },

  /**
   * Register a user with backend auth endpoint.
   */
  async register(payload: RegisterPayload): Promise<{ data: { session: Session | null }, error: Error | null }> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/register', payload)

      const session: Session = {
        access_token: response.data.access_token,
        user: response.data.user,
        expires_at: Date.now() + 24 * 60 * 60 * 1000,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))

      return { data: { session }, error: null }
    } catch (error) {
      return { data: { session: null }, error: error as Error }
    }
  },

  /**
   * Sign in with Google credential (from Google Sign-In SDK)
   */
  async signInWithGoogleCredential(credential: string): Promise<{ data: { session: Session | null }, error: Error | null }> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/google', {
        credential,
      })

      const session: Session = {
        access_token: response.data.access_token,
        user: response.data.user,
        expires_at: Date.now() + 24 * 60 * 60 * 1000,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))

      return { data: { session }, error: null }
    } catch (error) {
      return { data: { session: null }, error: error as Error }
    }
  },

  /**
   * Get current session from localStorage
   */
  async getSession(): Promise<{ data: { session: Session | null }, error: null }> {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      return { data: { session: null }, error: null }
    }

    try {
      const session: Session = JSON.parse(stored)
      if (session.expires_at < Date.now()) {
        localStorage.removeItem(STORAGE_KEY)
        return { data: { session: null }, error: null }
      }
      return { data: { session }, error: null }
    } catch {
      localStorage.removeItem(STORAGE_KEY)
      return { data: { session: null }, error: null }
    }
  },

  /**
   * Sign out - clear session from localStorage
   */
  async signOut(): Promise<{ error: null }> {
    localStorage.removeItem(STORAGE_KEY)
    return { error: null }
  },

  /**
   * Subscribe to auth state changes
   * Returns a subscription object for compatibility with Supabase API
   */
  onAuthStateChange(callback: (event: string, session: Session | null) => void) {
    // For native auth, we don't have real-time state changes
    // Just call the callback once with the current session
    this.getSession().then(({ data: { session } }) => {
      callback('INITIAL_SESSION', session)
    })

    return {
      data: {
        subscription: {
          unsubscribe: () => {
            // No-op for native auth
          },
        },
      },
    }
  },

  /**
   * Sign in with OTP (email magic link)
   */
  async signInWithOtp(config: { email: string; options?: { data?: Record<string, unknown>; emailRedirectTo?: string } }): Promise<{ data: Record<string, unknown>, error: Error | null }> {
    // OTP/magic link not implemented in backend yet
    return { data: {}, error: new Error('OTP sign-in not implemented') }
  },

  /**
   * Update user profile
   */
  async updateUser(updates: { data: { full_name?: string; avatar_url?: string } }): Promise<{ data: { user: User | null }, error: Error | null }> {
    try {
      const response = await apiClient.put<AuthResponse['user']>('/auth/profile', updates.data)

      // Update user in stored session
      const { data: { session } } = await this.getSession()
      if (session) {
        session.user = response.data
        localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
      }

      return { data: { user: response.data }, error: null }
    } catch (error) {
      return { data: { user: null }, error: error as Error }
    }
  },
}

// Export as 'supabase' for backward compatibility
export const supabase = {
  auth: nativeAuth,
}
