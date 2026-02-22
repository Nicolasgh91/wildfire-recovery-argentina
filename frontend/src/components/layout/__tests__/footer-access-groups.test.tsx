import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Footer } from '@/components/layout/footer'

let mockedIsAuthenticated = false

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: mockedIsAuthenticated ? { id: 'user-1' } : null,
    session: mockedIsAuthenticated ? { access_token: 'token' } : null,
    role: mockedIsAuthenticated ? 'user' : 'anonymous',
    status: mockedIsAuthenticated ? 'authenticated' : 'unauthenticated',
    isAuthenticated: mockedIsAuthenticated,
    signOut: vi.fn(),
    signIn: vi.fn(),
    signInWithGoogle: vi.fn(),
    signInWithOtp: vi.fn(),
    signUpWithEmail: vi.fn(),
  }),
}))

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) =>
      (
        {
          footerProduct: 'Producto',
          footerSupport: 'Soporte',
          footerInformative: 'Informativos',
          footerPublicSources: 'Fuentes publicas',
          home: 'Inicio',
          map: 'Mapa',
          reports: 'Exploracion satelital',
          fireHistory: 'Historicos',
          audit: 'Verificar terreno',
          footerLinkFaq: 'FAQ',
          footerLinkManual: 'Manual',
          footerLinkGlossary: 'Glosario',
          footerLinkContact: 'Contacto',
          footerLinkApiDocs: 'API Docs',
          footerExternalProtectedAreasLabel: 'Parques nacionales',
          footerExternalDailyReportLabel: 'Reporte diario de incendios',
          footerExternalSnmfLabel: 'SNMF',
          footerExternalBoletinLabel: 'Boletin Oficial',
          footerExternalConaeLabel: 'CONAE',
          footerExternalSmnLabel: 'SMN',
          footerExternalSpmfLabel: 'SPMF Chubut',
          footerExternalSplifLabel: 'SPLIF Rio Negro',
          footerExternalSnmfTooltip: 'SNMF tooltip',
          footerExternalBoletinTooltip: 'Boletin tooltip',
          footerExternalConaeTooltip: 'CONAE tooltip',
          footerExternalSmnTooltip: 'SMN tooltip',
          footerExternalSpmfTooltip: 'SPMF tooltip',
          footerExternalSplifTooltip: 'SPLIF tooltip',
          footerBrandLine1: 'linea 1',
          footerBrandLine2: 'linea 2',
          footerCopyright: 'Todos los derechos reservados',
          footerMadeWith: 'Hecho con',
          footerProtectForests: 'para proteger nuestros bosques',
        } as Record<string, string>
      )[key] ?? key,
  }),
}))

vi.mock('@/features/navigation/components/external-confirm-dialog', () => ({
  ExternalConfirmDialog: () => null,
}))

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

function renderFooter() {
  return render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>,
  )
}

describe('Footer access groups', () => {
  it('desktop support excludes contact and informative includes contact', () => {
    mockedIsAuthenticated = false
    renderFooter()

    const supportHeading = screen.getByRole('heading', { name: 'Soporte' })
    const supportColumn = supportHeading.parentElement
    expect(supportColumn).not.toBeNull()
    expect(within(supportColumn!).getByRole('link', { name: 'FAQ' })).toBeInTheDocument()
    expect(within(supportColumn!).getByRole('link', { name: 'Manual' })).toBeInTheDocument()
    expect(within(supportColumn!).getByRole('link', { name: 'Glosario' })).toBeInTheDocument()
    expect(within(supportColumn!).queryByRole('link', { name: 'Contacto' })).not.toBeInTheDocument()

    const informativeHeading = screen.getByRole('heading', { name: 'Informativos' })
    const informativeColumn = informativeHeading.parentElement
    expect(informativeColumn).not.toBeNull()
    expect(within(informativeColumn!).getByRole('button', { name: 'API Docs' })).toBeInTheDocument()
    expect(
      within(informativeColumn!).getByRole('button', { name: 'Parques nacionales' }),
    ).toBeInTheDocument()
    expect(
      within(informativeColumn!).getByRole('button', { name: 'Reporte diario de incendios' }),
    ).toBeInTheDocument()
    expect(within(informativeColumn!).getByRole('link', { name: 'Contacto' })).toBeInTheDocument()
  })

  it('desktop product includes auth-only entries only when user is authenticated', () => {
    mockedIsAuthenticated = false
    const { rerender } = renderFooter()

    const productHeading = screen.getByRole('heading', { name: 'Producto' })
    const productColumn = productHeading.parentElement
    expect(productColumn).not.toBeNull()
    expect(within(productColumn!).getByRole('link', { name: 'Inicio' })).toBeInTheDocument()
    expect(within(productColumn!).getByRole('link', { name: 'Mapa' })).toBeInTheDocument()
    expect(
      within(productColumn!).getByRole('link', { name: 'Exploracion satelital' }),
    ).toBeInTheDocument()
    expect(
      within(productColumn!).queryByRole('link', { name: 'Verificar terreno' }),
    ).not.toBeInTheDocument()
    expect(
      within(productColumn!).queryByRole('link', { name: 'Historicos' }),
    ).not.toBeInTheDocument()

    mockedIsAuthenticated = true
    rerender(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    )

    const productHeadingAuthenticated = screen.getByRole('heading', { name: 'Producto' })
    const productColumnAuthenticated = productHeadingAuthenticated.parentElement
    expect(productColumnAuthenticated).not.toBeNull()
    expect(
      within(productColumnAuthenticated!).getByRole('link', { name: 'Verificar terreno' }),
    ).toBeInTheDocument()
    expect(
      within(productColumnAuthenticated!).getByRole('link', { name: 'Historicos' }),
    ).toBeInTheDocument()
  })
})
