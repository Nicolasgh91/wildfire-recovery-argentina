import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { FireCard } from '@/components/fires/fire-card'
import { TooltipProvider } from '@/components/ui/tooltip'
import { I18nProvider } from '@/context/LanguageContext'
import type { EpisodeListItem } from '@/types/episode'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    }
})

// Suppress embla-carousel-react missing ref warning in test env
vi.mock('@/components/ui/carousel', () => ({
    Carousel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    CarouselContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    CarouselItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    CarouselNext: () => null,
    CarouselPrevious: () => null,
}))

function makeEpisode(overrides: Partial<EpisodeListItem> = {}): EpisodeListItem {
    return {
        id: 'ep-1',
        status: 'active',
        start_date: '2026-01-18T00:00:00Z',
        end_date: null,
        event_count: 3,
        detection_count: 42,
        provinces: ['Chubut'],
        estimated_area_hectares: 700.6,
        frp_max: 30,
        slides_data: [
            { type: 'NDVI', thumbnail_url: 'https://example.com/thumb.png', url: 'https://example.com/img.png' },
        ],
        representative_event_id: 'ev-1',
        is_recent: false,
        ...overrides,
    }
}

function renderCard(episode: EpisodeListItem) {
    return render(
        <MemoryRouter>
            <I18nProvider>
                <TooltipProvider>
                    <FireCard fire={episode} />
                </TooltipProvider>
            </I18nProvider>
        </MemoryRouter>,
    )
}

describe('FireCard', () => {
    beforeEach(() => {
        mockNavigate.mockClear()
        sessionStorage.clear()
        localStorage.setItem('fg:language', 'es')
    })

    // ─── Title ───────────────────────────────────────────────────

    it('renders province as title without "Incendio en"', () => {
        renderCard(makeEpisode({ provinces: ['Chubut'] }))
        const heading = screen.getByRole('heading', { level: 3 })
        expect(heading.textContent).toBe('Chubut')
        expect(heading.textContent).not.toContain('Incendio en')
    })

    it('renders multi-province title with count', () => {
        renderCard(makeEpisode({ provinces: ['Chubut', 'Río Negro'] }))
        const heading = screen.getByRole('heading', { level: 3 })
        expect(heading.textContent).toBe('Chubut (+1)')
    })

    it('renders fallback title when provinces is empty', () => {
        renderCard(makeEpisode({ provinces: [] }))
        const heading = screen.getByRole('heading', { level: 3 })
        expect(heading.textContent).toBe('Sin provincia')
    })

    // ─── Primary badge (image overlay) ──────────────────────────

    it('renders exactly one primary status badge inside image container', () => {
        renderCard(makeEpisode({ status: 'active' }))
        const imageContainer = screen.getByTestId('card-image')
        const badges = within(imageContainer).getAllByText('Activo')
        expect(badges).toHaveLength(1)
    })

    it('falls back to Extinto badge for unknown status', () => {
        renderCard(makeEpisode({ status: 'unknown' as any }))
        const imageContainer = screen.getByTestId('card-image')
        // resolveStatus defaults unknown values to 'extinct' → renders 'Extinto'
        expect(within(imageContainer).getByText('Extinto')).toBeTruthy()
    })

    it('secondary badges row does not contain the status label', () => {
        renderCard(makeEpisode({ status: 'monitoring' }))
        const secondary = screen.getByTestId('secondary-badges')
        expect(within(secondary).queryByText('Monitoreo')).toBeNull()
    })

    // ─── Secondary badges ──────────────────────────────────────

    it('renders Reciente badge when is_recent is true', () => {
        renderCard(makeEpisode({ is_recent: true }))
        const secondary = screen.getByTestId('secondary-badges')
        expect(within(secondary).getByText('Reciente')).toBeTruthy()
    })

    it('does not render Reciente badge when is_recent is false', () => {
        renderCard(makeEpisode({ is_recent: false }))
        const secondary = screen.getByTestId('secondary-badges')
        expect(within(secondary).queryByText('Reciente')).toBeNull()
    })

    it('renders Camera icon when no slides available', () => {
        renderCard(makeEpisode({ slides_data: null }))
        expect(screen.getByTestId('image-pending-icon')).toBeTruthy()
    })

    it('does not render Camera icon when slides are available', () => {
        renderCard(makeEpisode()) // default has slides_data
        expect(screen.queryByTestId('image-pending-icon')).toBeNull()
    })

    // ─── Severity badge ────────────────────────────────────────

    it('renders severity badge in secondary row', () => {
        renderCard(makeEpisode({ frp_max: 60 }))
        const secondary = screen.getByTestId('secondary-badges')
        expect(within(secondary).getByText('Alta')).toBeTruthy()
    })

    // ─── Subtitle ──────────────────────────────────────────────

    it('renders date and hectares in subtitle', () => {
        renderCard(makeEpisode())
        // formatDate returns locale string, formatHectares returns "700,6 ha"
        expect(screen.getByText(/700,6 ha/)).toBeTruthy()
    })

    // ─── CTA ───────────────────────────────────────────────────

    it('renders Ver detalles button', () => {
        renderCard(makeEpisode())
        expect(screen.getByText('Ver detalles')).toBeTruthy()
    })

    it('navigates to fire detail with return context on click', () => {
        // Mock scrollY
        Object.defineProperty(window, 'scrollY', { value: 420, writable: true })
        renderCard(makeEpisode())

        fireEvent.click(screen.getByText('Ver detalles'))

        expect(mockNavigate).toHaveBeenCalledWith('/fires/ev-1', {
            state: { returnTo: 'home', home: { scrollY: 420 } },
        })
        // Should also persist to sessionStorage
        const stored = JSON.parse(sessionStorage.getItem('fg:return_context')!)
        expect(stored.returnTo).toBe('home')
        expect(stored.home.scrollY).toBe(420)
    })
})
