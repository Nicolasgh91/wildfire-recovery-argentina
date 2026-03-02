import { useEffect, useMemo, useRef, useState, lazy, Suspense } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, RefreshCcw, Trees, ArrowUp, ArrowDown } from 'lucide-react'
import { BrandLogo } from '@/components/brand/BrandLogo'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import { useEpisodesByMode } from '@/hooks/queries/useEpisodesByMode'
import { FireCardSkeleton } from '@/components/fires/fire-card'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'
import type { RestoreContext } from '@/types/navigation'

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
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

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

  // Cargar episodios activos con ordenamiento
  const { data: activeData, isLoading: loadingActive, isError: errorActive, refetch: refetchActive } = useEpisodesByMode(
    'active', 
    DEFAULT_LIMIT, 
    true,
    { sort_by: 'start_date', sort_desc: sortOrder === 'desc' }
  )
  const activeEpisodes = activeData?.episodes ?? []

  const displayEpisodes = useMemo(() => {
    return activeEpisodes
  }, [activeEpisodes])

  const filteredEpisodes = useMemo(() => {
    return displayEpisodes.filter((episode) => {
      const province = episode.provinces?.[0]
      const matchesProvince = selectedProvince === 'all' || province === selectedProvince
      return matchesProvince
    })
  }, [displayEpisodes, selectedProvince])

  // Loading y error states
  const isLoading = loadingActive
  const isError = errorActive

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
      <div className="container mx-auto px-4 py-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center sm:hidden">
            <BrandLogo size="sm" />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Suspense fallback={null}>
              <FireFilters
                selectedProvince={selectedProvince}
                onProvinceChange={setSelectedProvince}
              />
            </Suspense>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
              className="gap-2"
              title={sortOrder === 'desc' ? t('sortNewestFirst') : t('sortOldestFirst')}
            >
              {sortOrder === 'desc' ? <ArrowDown className="h-4 w-4" /> : <ArrowUp className="h-4 w-4" />}
              {t('sortByDate')}
            </Button>
            <Button asChild variant="outline" className="ml-auto gap-2 sm:ml-0">
              <Link to="/fires/history">
                {t('fireHistory')}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div ref={gridRef} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {isError && !isLoading && (
            <div className="col-span-full rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive">
                    {t('fireLoadError')}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t('fireLoadErrorDetail')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    refetchActive()
                  }}
                  className="inline-flex items-center gap-1.5 rounded-md bg-destructive/20 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/30 transition-colors"
                >
                  <RefreshCcw className="h-3.5 w-3.5" />
                  {t('retry')}
                </button>
              </div>
            </div>
          )}
          {(!gridVisible || isLoading) && !isError && <FireCardSkeleton />}
          {gridVisible &&
            !isLoading &&
            !isError &&
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
