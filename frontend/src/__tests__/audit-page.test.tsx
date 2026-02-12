import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import AuditPage from '@/pages/Audit'

const searchAuditEpisodesMock = vi.fn()
const auditMutateMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    session: null,
    status: 'unauthenticated',
    role: 'anonymous',
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signUpWithEmail: vi.fn(),
    signOut: vi.fn(),
    isAuthenticated: false,
  }),
}))

vi.mock('@/hooks/mutations/useAudit', () => ({
  useAuditMutation: () => ({
    mutate: auditMutateMock,
    reset: vi.fn(),
    isPending: false,
    error: null,
    data: null,
  }),
}))

vi.mock('@/services/endpoints/audit-search', () => ({
  searchAuditEpisodes: (...args: unknown[]) => searchAuditEpisodesMock(...args),
}))

vi.mock('@/components/audit-map', () => ({
  AuditMap: () => <div data-testid="audit-map" />,
}))

describe('AuditPage auth gating', () => {
  it('does not call audit endpoints when unauthenticated', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <I18nProvider>
          <AuditPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    await user.type(screen.getByTestId('search-place'), 'Chubut')
    await user.click(screen.getByTestId('audit-submit'))

    expect(searchAuditEpisodesMock).not.toHaveBeenCalled()
    expect(auditMutateMock).not.toHaveBeenCalled()
    expect(screen.getByText('Inicia sesion para continuar.')).toBeInTheDocument()
  })
})
