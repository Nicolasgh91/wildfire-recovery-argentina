import { useEffect, useMemo, useRef, useState, lazy, Suspense } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Trees } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/context/LanguageContext'
import { useEpisodesByMode } from '@/hooks/queries/useEpisodesByMode'
import { FireCardSkeleton } from '@/components/fires/fire-card'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'
import type { RestoreContext } from '@/types/navigation'

const StoriesBar = lazy(() => import('@/components/stories-bar').then((m) => ({ default: m.StoriesBar })))
const FireCard = lazy(() => import('@/components/fires/fire-card').then((m) => ({ default: m.FireCard })))
const FireFilters = lazy(() => import('@/components/fire-filters').then((m) => ({ default: m.FireFilters })))

const DEFAULT_LIMIT = 20

export default function HomePage() {
  const { t } = useI18n()
  const location = useLocation()
  const navigate = useNavigate()
  const [selectedProvince, setSelectedProvince] = useState('all')
  const gridRef = useRef<HTMLDivElement | null>(null)
  const [gridVisible, setGridVisible] = useState(false)
  const [slideStage, setSlideStage] = useState(1) // 1: primer thumbnail, 2: segundo, 3: tercero
  const [showRecents, setShowRecents] = useState(false)

  // Restore scroll position when returning from fire detail
  useEffect(() => {
    const restoreState = (location.state as RestoreContext | null)?.restore
    let fromStorage = false

    let scrollY: number | undefined = restoreState?.scrollY

    if (scrollY === undefined) {
      try {
        const raw = sessionStorage.getItem(RETURN_CONTEXT_KEY)
        if (raw) {
          const ctx = JSON.parse(raw)
          if (ctx.returnTo === 'home' && ctx.home?.scrollY != null) {
            scrollY = ctx.home.scrollY
            fromStorage = true
          }
        }
      } catch { /* ignore */ }
    }

    if (scrollY !== undefined && scrollY > 0) {
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollY!)
      })
    }

    // Clean up: replace state to avoid re-applying on refresh
    if (restoreState) {
      navigate(location.pathname, { replace: true, state: null })
    }
    if (fromStorage) {
      sessionStorage.removeItem(RETURN_CONTEXT_KEY)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 1. Cargar episodios activos (siempre)
  const { data: activeData, isLoading: loadingActive } = useEpisodesByMode('active', DEFAULT_LIMIT)
  const activeEpisodes = activeData?.episodes ?? []

  // 2. Cargar recientes SOLO si el usuario los pide O si no hay activos
  //    (Lazy loading para evitar doble request inicial)
  const enableRecent = showRecents || (activeEpisodes.length === 0 && !loadingActive)
  const { data: recentData, isLoading: loadingRecent } = useEpisodesByMode(
    'recent',
    DEFAULT_LIMIT,
    enableRecent
  )
  const recentEpisodes = recentData?.episodes ?? []

  // Loading es true si cargamos activos O (estamos cargando recientes explícitamente)
  const isLoading = loadingActive || (enableRecent && loadingRecent)

  const displayEpisodes = useMemo(() => {
    // Si no hay activos, mostrar recientes (fallback)
    if (activeEpisodes.length === 0 && !loadingActive) return recentEpisodes

    // Si el usuario no pidió recientes, solo activos
    if (!showRecents) return activeEpisodes

    // Combinar ambos sin duplicados
    const seen = new Set<string>()
    const merged = []
    for (const episode of activeEpisodes) {
      seen.add(episode.id)
      merged.push(episode)
    }
    for (const episode of recentEpisodes) {
      if (!seen.has(episode.id)) {
        merged.push(episode)
      }
    }
    return merged
  }, [activeEpisodes, recentEpisodes, showRecents, loadingActive])

  const filteredEpisodes = useMemo(() => {
    return displayEpisodes.filter((episode) => {
      const province = episode.provinces?.[0]
      const matchesProvince = selectedProvince === 'all' || province === selectedProvince
      return matchesProvince
    })
  }, [displayEpisodes, selectedProvince])

  useEffect(() => {
    if (!gridRef.current) return
    const node = gridRef.current
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting) {
          setGridVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px 0px', threshold: 0.15 }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!gridVisible) return
    setSlideStage(1)
    const t1 = setTimeout(() => setSlideStage(2), 200)
    const t2 = setTimeout(() => setSlideStage(3), 400)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [gridVisible, displayEpisodes.length])

  return (
    <div className="min-h-screen bg-background">
      <Suspense fallback={null}>
        <StoriesBar fires={filteredEpisodes} />
      </Suspense>

      <div className="container mx-auto px-4 py-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Trees className="h-8 w-8 text-primary sm:hidden" />
            <h1 className="text-2xl font-bold text-foreground sm:hidden">{t('fireFeed')}</h1>
            <h1 className="hidden text-2xl font-bold text-foreground sm:block">
              {t('activeFiresArgentina')}
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Suspense fallback={null}>
              <FireFilters
                selectedProvince={selectedProvince}
                onProvinceChange={setSelectedProvince}
              />
            </Suspense>
            {/* Mostrar toggle solo si hay posibilidad de tener ambos o ya se cargaron */}
            {(activeEpisodes.length > 0 || showRecents) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Switch
                  id="show-recents"
                  checked={showRecents}
                  onCheckedChange={setShowRecents}
                />
                <label htmlFor="show-recents">{t('recentFiresToggle')}</label>
              </div>
            )}
            <Button asChild variant="outline" className="ml-auto gap-2 sm:ml-0">
              <Link to="/fires/history">
                {t('fireHistory')}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div ref={gridRef} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {(!gridVisible || isLoading) && <FireCardSkeleton />}
          {gridVisible &&
            !isLoading &&
            filteredEpisodes.map((episode) => (
              <Suspense key={episode.id} fallback={<FireCardSkeleton />}>
                <FireCard key={episode.id} fire={episode} slideStage={slideStage} />
              </Suspense>
            ))}
        </div>

        {!isLoading && filteredEpisodes.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Trees className="mb-4 h-16 w-16 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">
              {t('recentFiresEmpty')}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
