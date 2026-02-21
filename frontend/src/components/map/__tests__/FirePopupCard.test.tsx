import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { FirePopupCard } from '@/components/map/FirePopupCard'
import type { FireMapItem } from '@/types/map'

vi.mock('@/context/LanguageContext', () => ({
  useI18n: () => ({ t: (key: string) => key }),
}))

const baseFire: FireMapItem = {
  id: 'fire-1',
  title: 'Incendio de prueba',
  lat: -34,
  lon: -58,
  severity: 'medium',
  province: 'Buenos Aires',
  hectares: 230,
  in_protected_area: true,
  overlap_percentage: 12.5,
  protected_area_name: 'Reserva Test',
  count_protected_areas: 1,
}

describe('FirePopupCard', () => {
  it('applies internal scroll max-height style', () => {
    render(<FirePopupCard fire={baseFire} variant="default" maxBodyHeight={180} />)

    const body = screen.getByTestId('fire-popup-scroll')
    expect(body).toHaveStyle({ maxHeight: '180px' })
    expect(body.className).toContain('overflow-y-auto')
  })

  it('renders compact mode with sticky CTA and emits callback', () => {
    const onViewDetails = vi.fn()
    render(
      <FirePopupCard
        fire={baseFire}
        variant="default"
        compact
        maxBodyHeight={220}
        onViewDetails={onViewDetails}
      />,
    )

    const cta = screen.getByRole('button', { name: 'viewDetails' })
    expect(cta.className).toContain('sticky')
    fireEvent.click(cta)
    expect(onViewDetails).toHaveBeenCalledTimes(1)
  })

  it('renders fire_detail variant without CTA button', () => {
    render(<FirePopupCard fire={{ ...baseFire, status: 'active' }} variant="fire_detail" maxBodyHeight={200} />)

    expect(screen.getByText('firePopupTitleActive')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'viewDetails' })).not.toBeInTheDocument()
  })
})
