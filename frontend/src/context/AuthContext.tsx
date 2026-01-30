import { createContext, useContext, useState, type ReactNode } from 'react'

export type Role = 'guest' | 'user' | 'admin'

interface User {
  email: string
  role: Role
}

interface AuthContextType {
  user: User | null
  role: Role
  login: (email: string, password: string) => boolean
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function getRoleFromEmail(email: string): Role {
  if (email.includes('admin@') || email.endsWith('@forestguard.ar')) {
    return 'admin'
  }
  return 'user'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  const login = (email: string, password: string): boolean => {
    if (!email || !password) {
      return false
    }
    
    const role = getRoleFromEmail(email)
    setUser({ email, role })
    return true
  }

  const logout = () => {
    setUser(null)
  }

  const role: Role = user?.role || 'guest'
  const isAuthenticated = user !== null

  return (
    <AuthContext.Provider value={{ user, role, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
