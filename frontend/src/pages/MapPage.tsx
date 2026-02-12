import { Suspense, lazy, useMemo, useState } from 'react'
import { Map, List, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useI18n } from '@/context/LanguageContext'
import { useEpisodesByMode } from '@/hooks/queries/useEpisodesByMode'
import type { FireMapItem } from '@/types/map'

const FireMap = lazy(() =>
  import('@/components/fire-map').then((mod) => ({ default: mod.FireMap })),
)

const mapFallback = (
  <div className="flex h-full items-center justify-center bg-muted">
    <div className="text-center">
      <Map className="mx-auto mb-2 h-8 w-8 animate-pulse text-primary" />
      <p className="text-sm text-muted-foreground">Loading map...</p>
    </div>
  </div>
)

export default function MapPage() {
  const { t } = useI18n()
  const [selectedFire, setSelectedFire] = useState<FireMapItem | null>(null)
  const [showSidebar, setShowSidebar] = useState(true)
  const { data: activeData, isLoading: loadingActive } = useEpisodesByMode('active', 100)
  const { data: recentData, isLoading: loadingRecent } = useEpisodesByMode('recent', 100)
  const isLoading = loadingActive || loadingRecent

  const mapItems = useMemo(() => {
    const activeEpisodes = activeData?.episodes ?? []
    const recentEpisodes = recentData?.episodes ?? []
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
      .filter(
        (episode) =>
          episode.centroid_lat !== null &&
          episode.centroid_lat !== undefined &&
          episode.centroid_lon !== null &&
          episode.centroid_lon !== undefined
      )
      .map((episode) => {
        const frp = episode.frp_max ?? 0
        const severity = frp >= 50 ? 'high' : frp >= 20 ? 'medium' : 'low'
        const status =
          episode.status === 'active' || episode.status === 'monitoring'
            ? (episode.status as 'active' | 'monitoring')
            : 'extinguished'
        const title =
          episode.provinces && episode.provinces.length > 0
            ? `Incendio en ${episode.provinces[0]}`
            : 'Incendio sin provincia'
        return {
          id: episode.id,
          title,
          lat: Number(episode.centroid_lat),
          lon: Number(episode.centroid_lon),
          severity,
          province: episode.provinces?.[0] ?? null,
          status,
          hectares: episode.estimated_area_hectares ?? null,
          representative_event_id: episode.representative_event_id ?? episode.id,
        } satisfies FireMapItem
      })
  }, [activeData?.episodes, recentData?.episodes])

  return (
    <div className="relative h-full">
      <Suspense fallback={mapFallback}>
        <FireMap
          fires={mapItems}
          selectedFire={selectedFire}
          onFireSelect={setSelectedFire}
          height="h-full"
        />
      </Suspense>

      <Button
        variant="secondary"
        size="icon"
        className="absolute left-4 top-4 z-[400] md:hidden"
        onClick={() => setShowSidebar(!showSidebar)}
      >
        {showSidebar ? <X className="h-4 w-4" /> : <List className="h-4 w-4" />}
      </Button>

      {showSidebar && (
        <Card className="absolute right-4 top-4 z-[400] hidden w-80 md:block">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Map className="h-5 w-5 text-primary" />
              {t('interactiveMap')}
            </CardTitle>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">{t('mapLegendActive')}</Badge>
              <Badge variant="secondary">{t('mapLegendRecent')}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {isLoading && (
                  <div className="text-sm text-muted-foreground">{t('loading')}</div>
                )}
                {!isLoading && mapItems.length === 0 && (
                  <div className="text-sm text-muted-foreground">{t('recentFiresEmpty')}</div>
                )}
                {mapItems.map((fire) => (
                  <button
                    key={fire.id}
                    type="button"
                    onClick={() => setSelectedFire(fire)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted ${
                      selectedFire?.id === fire.id ? 'border-primary bg-primary/10' : 'border-border'
                    }`}
                  >
                    <p className="mb-1 line-clamp-1 font-medium text-foreground">{fire.title}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{fire.province}</span>
                      <Badge
                        variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {fire.hectares.toLocaleString()} ha
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {showSidebar && (
        <Card className="absolute bottom-4 left-4 right-4 z-[400] md:hidden">
          <CardContent className="p-3">
            <ScrollArea className="h-32">
              <div className="flex gap-2 pb-2">
                {mapItems.map((fire) => (
                  <button
                    key={fire.id}
                    type="button"
                    onClick={() => setSelectedFire(fire)}
                    className={`shrink-0 rounded-lg border p-2 text-left transition-colors ${
                      selectedFire?.id === fire.id ? 'border-primary bg-primary/10' : 'border-border'
                    }`}
                  >
                    <p className="w-24 truncate text-xs font-medium text-foreground">
                      {fire.province}
                    </p>
                    <Badge
                      variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                      className="mt-1 text-xs"
                    >
                      {fire.hectares.toLocaleString()} ha
                    </Badge>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
