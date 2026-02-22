import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RestrictedAccessDialog } from '@/components/auth/RestrictedAccessDialog'

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) =>
      (
        {
          protectedPageTitle: 'Acceso restringido',
          protectedPageMessage:
            'Esta pagina es exclusiva para usuarios registrados. Por favor, inicia sesion para continuar.',
          goBack: 'Volver atras',
          login: 'Iniciar sesion',
        } as Record<string, string>
      )[key] ?? key,
  }),
}))

describe('RestrictedAccessDialog', () => {
  it('renders title and message for restricted access', () => {
    render(
      <RestrictedAccessDialog
        open
        onOpenChange={vi.fn()}
        onGoBack={vi.fn()}
        onLogin={vi.fn()}
      />,
    )

    expect(screen.getByText('Acceso restringido')).toBeInTheDocument()
    expect(
      screen.getByText(
        'Esta pagina es exclusiva para usuarios registrados. Por favor, inicia sesion para continuar.',
      ),
    ).toBeInTheDocument()
  })

  it('triggers go back and login actions from buttons', async () => {
    const onGoBack = vi.fn()
    const onLogin = vi.fn()

    render(
      <RestrictedAccessDialog
        open
        onOpenChange={vi.fn()}
        onGoBack={onGoBack}
        onLogin={onLogin}
      />,
    )

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Volver atras' }))
    await user.click(screen.getByRole('button', { name: 'Iniciar sesion' }))

    expect(onGoBack).toHaveBeenCalledTimes(1)
    expect(onLogin).toHaveBeenCalledTimes(1)
  })
})
