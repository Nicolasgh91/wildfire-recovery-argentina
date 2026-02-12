import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import { setAuthToken } from '@/services/api'

export type UserRole = 'admin' | 'user' | 'anonymous'
export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthState {
  user: User | null
  session: Session | null
  status: AuthStatus
  role: UserRole
}

interface AuthContextValue extends AuthState {
  signIn: (email: string, password: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signUpWithEmail: (payload: { email: string; firstName: string; lastName: string }) => Promise<void>
  signOut: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function mapRole(user: User | null): UserRole {
  if (!user) return 'anonymous'
  const role = (user.app_metadata as { role?: string } | undefined)?.role
  return role === 'admin' ? 'admin' : 'user'
}

function buildState(session: Session | null): AuthState {
  return {
    user: session?.user ?? null,
    session,
    status: session ? 'authenticated' : 'unauthenticated',
    role: mapRole(session?.user ?? null),
  }
}

function resolveAuthRedirectUrl() {
  if (typeof window === 'undefined') return undefined
  return (
    import.meta.env.VITE_AUTH_REDIRECT_URL ||
    `${window.location.origin}/auth/callback`
  )
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    status: 'loading',
    role: 'anonymous',
  })

  const updateState = useCallback((session: Session | null) => {
    setState(buildState(session))
    setAuthToken(session?.access_token ?? null)
  }, [])

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return
      updateState(session)
    })

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!mounted) return
      updateState(session)
    })

    return () => {
      mounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }, [])

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    setAuthToken(null)
  }, [])

  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: resolveAuthRedirectUrl(),
      },
    })
    if (error) throw error
  }, [])

  const signUpWithEmail = useCallback(
    async (payload: { email: string; firstName: string; lastName: string }) => {
      const { error } = await supabase.auth.signInWithOtp({
        email: payload.email,
        options: {
          data: {
            full_name: `${payload.firstName} ${payload.lastName}`.trim(),
            first_name: payload.firstName,
            last_name: payload.lastName,
          },
          emailRedirectTo: resolveAuthRedirectUrl(),
        },
      })
      if (error) throw error
    },
    []
  )

  const isAuthenticated = state.status === 'authenticated'

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      signIn,
      signInWithGoogle,
      signUpWithEmail,
      signOut,
      isAuthenticated,
    }),
    [isAuthenticated, signIn, signInWithGoogle, signOut, signUpWithEmail, state]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
