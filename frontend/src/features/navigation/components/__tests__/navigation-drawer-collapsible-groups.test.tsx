import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { NavigationDrawerCollapsibleGroups } from '@/features/navigation/components/navigation-drawer-collapsible-groups'

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({
    t: (key: string) =>
      (
        {
          footerSupport: 'Soporte',
          navMoreInformation: 'Mas informacion',
          footerPublicSources: 'Fuentes publicas',
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
        } as Record<string, string>
      )[key] ?? key,
  }),
}))

describe('NavigationDrawerCollapsibleGroups', () => {
  it('renders soporte, mas informacion and fuentes publicas sections', () => {
    render(
      <MemoryRouter>
        <NavigationDrawerCollapsibleGroups
          isAuthenticated
          onInternalNavigate={vi.fn()}
          onExternalNavigate={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: 'Soporte' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mas informacion' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fuentes publicas' })).toBeInTheDocument()
  })

  it('shows mobile support and more information links, and routes external actions through callback', async () => {
    const onInternalNavigate = vi.fn()
    const onExternalNavigate = vi.fn()

    render(
      <MemoryRouter>
        <NavigationDrawerCollapsibleGroups
          isAuthenticated
          onInternalNavigate={onInternalNavigate}
          onExternalNavigate={onExternalNavigate}
        />
      </MemoryRouter>,
    )

    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Soporte' }))
    expect(screen.getByRole('link', { name: 'FAQ' })).toHaveAttribute('href', '/faq')
    expect(screen.getByRole('link', { name: 'Manual' })).toHaveAttribute('href', '/manual')
    expect(screen.getByRole('link', { name: 'Glosario' })).toHaveAttribute('href', '/glossary')
    await user.click(screen.getByRole('link', { name: 'Contacto' }))
    expect(onInternalNavigate).toHaveBeenCalledWith('/contact')

    await user.click(screen.getByRole('button', { name: 'Mas informacion' }))
    await user.click(screen.getByRole('button', { name: 'API Docs' }))
    expect(onExternalNavigate).toHaveBeenCalledWith({
      href: 'https://forestguard.freedynamicdns.org/docs',
      siteName: 'API Docs',
    })
    await user.click(screen.getByRole('button', { name: 'Parques nacionales' }))
    expect(onExternalNavigate).toHaveBeenCalledWith({
      href: 'https://www.argentina.gob.ar/parquesnacionales',
      siteName: 'Parques nacionales',
    })
    await user.click(screen.getByRole('button', { name: 'Reporte diario de incendios' }))
    expect(onExternalNavigate).toHaveBeenCalledWith({
      href: 'https://www.argentina.gob.ar/reporte-diario-de-incendios',
      siteName: 'Reporte diario de incendios',
    })

    await user.click(screen.getByRole('button', { name: 'Fuentes publicas' }))
    expect(screen.getByRole('button', { name: 'SNMF' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'SNMF' }))
    expect(onExternalNavigate).toHaveBeenCalledWith({
      href: 'https://www.argentina.gob.ar/servicio-nacional-de-manejo-del-fuego',
      siteName: 'SNMF',
    })
  })
})
