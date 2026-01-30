import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { I18nProvider } from '@/context/LanguageContext'
import MapPage from '@/pages/MapPage'

vi.mock('@/components/fire-map', () => ({
  FireMap: () => <div data-testid="fire-map" />,
}))

describe('MapPage', () => {
  it('renders the map layout with fire list content', async () => {
    render(
      <I18nProvider>
        <MapPage />
      </I18nProvider>,
    )

    expect(screen.getByText('Mapa Interactivo')).toBeInTheDocument()
    expect(await screen.findByTestId('fire-map')).toBeInTheDocument()

    const provinceMatches = screen.getAllByText('Chubut')
    expect(provinceMatches.length).toBeGreaterThan(0)
  })
})
