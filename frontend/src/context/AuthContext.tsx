import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { supabase } from '@/lib/auth'

// Type definitions to match Supabase types
type User = {
  id: string
  email: string
  full_name: string | null
  role: string
  avatar_url: string | null
}

type Session = {
  access_token: string
  user: User
  expires_at: number
}

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
  signUpWithEmail: (payload: {
    email: string
    password: string
    firstName: string
    lastName: string
    dni: string
  }) => Promise<void>
  signOut: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function mapRole(user: User | null): UserRole {
  if (!user) return 'anonymous'
  return user.role === 'admin' ? 'admin' : 'user'
}

function buildState(session: Session | null): AuthState {
  return {
    user: session?.user ?? null,
    session,
    status: session ? 'authenticated' : 'unauthenticated',
    role: mapRole(session?.user ?? null),
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    status: 'loading',
    role: 'anonymous',
  })

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return
      setState(buildState(session))
    })

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!mounted) return
      setState(buildState(session))
    })

    return () => {
      mounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword(email, password)
    if (error) throw error
    setState(buildState(data.session))
  }, [])

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    setState(buildState(null))
  }, [])

  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    })
    if (error) throw error

    const { data: { session } } = await supabase.auth.getSession()
    setState(buildState(session))
  }, [])

  const signUpWithEmail = useCallback(
    async (payload: {
      email: string
      password: string
      firstName: string
      lastName: string
      dni: string
    }) => {
      const { data, error } = await supabase.auth.register({
        email: payload.email,
        password: payload.password,
        dni: payload.dni,
        full_name: `${payload.firstName} ${payload.lastName}`.trim(),
      })
      if (error) throw error
      setState(buildState(data.session))
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
