import { useEffect, useMemo, useRef, useState, lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Trees } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/context/LanguageContext'
import { useActiveEpisodes } from '@/hooks/queries/useActiveEpisodes'
import { useEpisodesByMode } from '@/hooks/queries/useEpisodesByMode'
import { FireCardSkeleton } from '@/components/fires/fire-card'

const StoriesBar = lazy(() => import('@/components/stories-bar').then((m) => ({ default: m.StoriesBar })))
const FireCard = lazy(() => import('@/components/fires/fire-card').then((m) => ({ default: m.FireCard })))
const FireFilters = lazy(() => import('@/components/fire-filters').then((m) => ({ default: m.FireFilters })))

const DEFAULT_LIMIT = 20

export default function HomePage() {
  const { t } = useI18n()
  const [selectedProvince, setSelectedProvince] = useState('all')
  const gridRef = useRef<HTMLDivElement | null>(null)
  const [gridVisible, setGridVisible] = useState(false)
  const [slideStage, setSlideStage] = useState(1) // 1: primer thumbnail, 2: segundo, 3: tercero
  const [showRecents, setShowRecents] = useState(false)

  const { data: activeData, isLoading: loadingActive } = useActiveEpisodes(DEFAULT_LIMIT)
  const { data: recentData, isLoading: loadingRecent } = useEpisodesByMode('recent', DEFAULT_LIMIT)
  const activeEpisodes = (activeData?.episodes ?? []).filter(
    (episode) => episode.status === 'active' || episode.status === 'monitoring',
  )
  const recentEpisodes = (recentData?.episodes ?? []).filter(
    (episode) =>
      episode.is_recent === true &&
      (episode.status === 'extinct' || episode.status === 'closed'),
  )
  const isLoading = loadingActive || loadingRecent

  const displayEpisodes = useMemo(() => {
    const withThumbnails = (episodes: typeof activeEpisodes) =>
      episodes.filter((episode) =>
        (episode.slides_data ?? []).some((slide) => Boolean(slide.thumbnail_url || slide.url)),
      )

    const activeWithThumbnails = withThumbnails(activeEpisodes)
    const recentWithThumbnails = withThumbnails(recentEpisodes)

    if (activeWithThumbnails.length === 0) return recentWithThumbnails
    if (!showRecents) return activeWithThumbnails

    const seen = new Set<string>()
    const merged = []
    for (const episode of activeWithThumbnails) {
      seen.add(episode.id)
      merged.push(episode)
    }
    for (const episode of recentWithThumbnails) {
      if (!seen.has(episode.id)) {
        merged.push(episode)
      }
    }
    return merged
  }, [activeEpisodes, recentEpisodes, showRecents])

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
            {activeEpisodes.length > 0 && recentEpisodes.length > 0 && (
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
