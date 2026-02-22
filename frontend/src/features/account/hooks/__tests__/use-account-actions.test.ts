import { describe, expect, it, beforeEach, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAccountActions } from '@/features/account/hooks/use-account-actions'
import { useAuth } from '@/context/AuthContext'
import { supabase } from '@/lib/supabase'
import { apiClient } from '@/services/api'

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      updateUser: vi.fn(),
      resetPasswordForEmail: vi.fn(),
    },
  },
}))

vi.mock('@/services/api', () => ({
  apiClient: {
    post: vi.fn(),
  },
}))

describe('useAccountActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue({
      user: {
        email: 'qa@example.com',
        app_metadata: { providers: ['email'] },
        identities: [{ provider: 'email' }],
      } as any,
      signOut: vi.fn().mockResolvedValue(undefined),
      session: null,
      status: 'authenticated',
      role: 'user',
      signIn: vi.fn(),
      signInWithGoogle: vi.fn(),
      signInWithOtp: vi.fn(),
      signUpWithEmail: vi.fn(),
      isAuthenticated: true,
    })
  })

  it('requires current password for non-oauth password update', async () => {
    const { result } = renderHook(() => useAccountActions())
    await expect(
      result.current.updatePassword({ newPassword: 'new-password-123' }),
    ).rejects.toThrow('Current password is required')
  })

  it('reauthenticates and updates password for email users', async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValue({ error: null } as any)
    vi.mocked(supabase.auth.updateUser).mockResolvedValue({ error: null } as any)

    const { result } = renderHook(() => useAccountActions())
    await result.current.updatePassword({
      currentPassword: 'old-password-123',
      newPassword: 'new-password-123',
    })

    expect(supabase.auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'qa@example.com',
      password: 'old-password-123',
    })
    expect(supabase.auth.updateUser).toHaveBeenCalledWith({
      password: 'new-password-123',
    })
  })

  it('calls account delete endpoints through api client', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} } as any)
    const { result } = renderHook(() => useAccountActions())

    await result.current.requestDeleteChallenge()
    await result.current.deleteAccount({
      confirmationText: 'ELIMINAR',
      challengeToken: '123456',
    })

    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/account/delete/challenge')
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/account/delete', {
      confirmationText: 'ELIMINAR',
      challengeToken: '123456',
    })
  })
})
