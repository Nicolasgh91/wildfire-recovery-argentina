import { describe, expect, it, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PasswordSecurityCard } from '@/features/account/components/password-security-card'
import { useAccountActions } from '@/features/account/hooks/use-account-actions'

vi.mock('@/features/account/hooks/use-account-actions', () => ({
  RESET_PASSWORD_NEUTRAL_MESSAGE:
    'Si existe una cuenta asociada a este correo, recibiras un enlace para restablecer tu contrasena.',
  useAccountActions: vi.fn(),
}))

describe('PasswordSecurityCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAccountActions).mockReturnValue({
      isOAuthUser: false,
      reauthenticate: vi.fn(),
      updatePassword: vi.fn().mockResolvedValue(undefined),
      sendPasswordReset: vi.fn().mockResolvedValue({ message: 'ok' }),
      logout: vi.fn(),
      requestDeleteChallenge: vi.fn(),
      deleteAccount: vi.fn(),
    })
  })

  it('submits password update with current password for email accounts', async () => {
    const updatePassword = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useAccountActions).mockReturnValue({
      isOAuthUser: false,
      reauthenticate: vi.fn(),
      updatePassword,
      sendPasswordReset: vi.fn().mockResolvedValue({ message: 'ok' }),
      logout: vi.fn(),
      requestDeleteChallenge: vi.fn(),
      deleteAccount: vi.fn(),
    })

    render(<PasswordSecurityCard />)
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Contrasena actual'), 'old-password')
    await user.type(screen.getByLabelText('Nueva contrasena'), 'new-password-123')
    await user.type(screen.getByLabelText('Confirmar nueva contrasena'), 'new-password-123')
    await user.click(screen.getByRole('button', { name: 'Actualizar contrasena' }))

    expect(updatePassword).toHaveBeenCalledWith({
      currentPassword: 'old-password',
      newPassword: 'new-password-123',
    })
  })

  it('hides current password field for oauth accounts', () => {
    vi.mocked(useAccountActions).mockReturnValue({
      isOAuthUser: true,
      reauthenticate: vi.fn(),
      updatePassword: vi.fn().mockResolvedValue(undefined),
      sendPasswordReset: vi.fn().mockResolvedValue({ message: 'ok' }),
      logout: vi.fn(),
      requestDeleteChallenge: vi.fn(),
      deleteAccount: vi.fn(),
    })

    render(<PasswordSecurityCard />)

    expect(screen.queryByLabelText('Contrasena actual')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Esta cuenta usa proveedor OAuth. Usa reset por correo para definir una contrasena local si aplica.',
      ),
    ).toBeInTheDocument()
  })
})
