import { useMemo } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/context/AuthContext'
import { apiClient } from '@/services/api'

const RESET_PASSWORD_NEUTRAL_MESSAGE =
  'Si existe una cuenta asociada a este correo, recibiras un enlace para restablecer tu contrasena.'

function getPrimaryProvider(user: ReturnType<typeof useAuth>['user']): string | null {
  const appMetadataProviders = (user?.app_metadata as { providers?: string[] } | undefined)?.providers
  if (appMetadataProviders && appMetadataProviders.length > 0) {
    return appMetadataProviders[0] ?? null
  }

  const identities = user?.identities
  if (identities && identities.length > 0) {
    return identities[0]?.provider ?? null
  }

  return null
}

export function useAccountActions() {
  const { user, signOut } = useAuth()

  const authProvider = useMemo(() => getPrimaryProvider(user), [user])
  const isOAuthUser = authProvider !== null && authProvider !== 'email'

  const reauthenticate = async (currentPassword: string): Promise<void> => {
    const email = user?.email
    if (!email) {
      throw new Error('No active user email')
    }

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password: currentPassword,
    })

    if (error) {
      throw new Error('Reauthentication failed')
    }
  }

  const updatePassword = async (params: { newPassword: string; currentPassword?: string }) => {
    if (!params.newPassword || params.newPassword.length < 8) {
      throw new Error('Invalid password')
    }

    if (!isOAuthUser) {
      if (!params.currentPassword) {
        throw new Error('Current password is required')
      }
      await reauthenticate(params.currentPassword)
    }

    const { error } = await supabase.auth.updateUser({ password: params.newPassword })
    if (error) {
      throw new Error('Password update failed')
    }
  }

  const sendPasswordReset = async (email?: string): Promise<{ message: string }> => {
    const targetEmail = email ?? user?.email ?? ''
    if (!targetEmail) {
      return { message: RESET_PASSWORD_NEUTRAL_MESSAGE }
    }

    await supabase.auth.resetPasswordForEmail(targetEmail)
    return { message: RESET_PASSWORD_NEUTRAL_MESSAGE }
  }

  const logout = async () => {
    await signOut()
  }

  const requestDeleteChallenge = async () => {
    await apiClient.post('/account/delete/challenge')
  }

  const deleteAccount = async (payload: {
    confirmationText: string
    password?: string
    challengeToken?: string
    reason?: string
  }) => {
    await apiClient.post('/account/delete', payload)
  }

  return {
    isOAuthUser,
    reauthenticate,
    updatePassword,
    sendPasswordReset,
    logout,
    requestDeleteChallenge,
    deleteAccount,
  }
}

export { RESET_PASSWORD_NEUTRAL_MESSAGE }
