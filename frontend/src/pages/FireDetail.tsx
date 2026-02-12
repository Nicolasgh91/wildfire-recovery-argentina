import { Suspense, lazy } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Calendar,
  Download,
  FileText,
  Flame,
  MapPin,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from '@/components/ui/carousel'
import { Skeleton } from '@/components/ui/skeleton'
import { QualityIndicator } from '@/components/fires/QualityIndicator'
import { useI18n } from '@/context/LanguageContext'
import { useFire } from '@/hooks/queries/useFire'
import { useFireQuality } from '@/hooks/queries/useFireQuality'
import {
  formatDate,
  formatHectares,
  getFireTitle,
  type FireStatus,
} from '@/types/fire'
import type { FireMapItem } from '@/types/map'

const FireMap = lazy(() =>
  import('@/components/fire-map').then((mod) => ({ default: mod.FireMap })),
)

const mapFallback = (
  <div className="flex h-64 items-center justify-center rounded-lg bg-muted">
    <p className="text-sm text-muted-foreground">Loading map...</p>
  </div>
)

const FRP_MEDIUM_THRESHOLD = 20
const FRP_HIGH_THRESHOLD = 50

function resolveStatus(status: FireStatus | undefined, endDate?: string | null): FireStatus {
  if (status) return status
  if (!endDate) return 'extinguished'
  const end = new Date(endDate)
  if (Number.isNaN(end.getTime())) return 'extinguished'
  return end >= new Date() ? 'active' : 'extinguished'
}

function resolveSeverityLevel(maxFrp?: number | null): 'high' | 'medium' | 'low' {
  if (maxFrp === null || maxFrp === undefined || Number.isNaN(maxFrp)) return 'low'
  if (maxFrp >= FRP_HIGH_THRESHOLD) return 'high'
  if (maxFrp >= FRP_MEDIUM_THRESHOLD) return 'medium'
  return 'low'
}

function FireDetailSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="h-64 md:h-80">
        <Skeleton className="h-full w-full rounded-none" />
      </div>
      <div className="container mx-auto space-y-6 px-4 py-6">
        <Skeleton className="h-8 w-2/3" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={`card-${index}`} className="h-20 w-full" />
          ))}
        </div>
        <div className="grid gap-6">
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      </div>
    </div>
  )
}

export default function FireDetailPage() {
  const { t } = useI18n()
  const { id } = useParams<{ id: string }>()
  const fireId = id ?? ''

  const {
    data,
    isLoading,
    error,
  } = useFire(fireId)

  const isEpisodeDetail = data?.source_type === 'episode'
  const qualityId = !isEpisodeDetail ? data?.fire?.id ?? '' : ''

  const {
    data: quality,
    isLoading: qualityLoading,
    error: qualityError,
  } = useFireQuality(qualityId)

  const fire = data?.fire ?? null
  const title = fire ? getFireTitle(fire.department ?? undefined, fire.province ?? undefined) : ''
  const severityLevel = resolveSeverityLevel(fire?.max_frp ?? null)
  const statusKey = resolveStatus(fire?.status, fire?.end_date)
  const centroid = fire?.centroid
  const protectedAreaNames = (() => {
    const rawNames: Array<string | null | undefined> =
      fire?.protected_areas && fire.protected_areas.length
        ? fire.protected_areas.map((area) => area.name)
        : fire?.protected_area_name
          ? fire.protected_area_name.split(',')
          : []

    const unique: string[] = []
    const seen = new Set<string>()

    for (const name of rawNames) {
      if (!name) continue
      const normalized = name.trim().replace(/\s+/g, ' ')
      if (!normalized) continue
      const key = normalized.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      unique.push(normalized)
    }

    return unique.length ? unique.join(', ') : null
  })()
  const mapFire: FireMapItem | null =
    fire && centroid && Number.isFinite(centroid.latitude) && Number.isFinite(centroid.longitude)
      ? {
          id: fire.id,
          title,
          lat: centroid.latitude,
          lon: centroid.longitude,
          severity: severityLevel,
          province: fire.province ?? undefined,
          status: statusKey,
          date: fire.start_date,
          hectares: fire.estimated_area_hectares ?? null,
          in_protected_area: fire.in_protected_area,
          overlap_percentage: fire.overlap_percentage ?? null,
          protected_area_name: protectedAreaNames,
          count_protected_areas: fire.count_protected_areas ?? null,
        }
      : null

  if (isLoading) {
    return <FireDetailSkeleton />
  }

  const errorStatus = (error as { response?: { status?: number } })?.response?.status

  if (errorStatus === 404) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-12 text-center">
          <p className="mb-4 text-lg font-semibold text-foreground">Incendio no disponible.</p>
          <Button asChild variant="secondary">
            <Link to="/fires/history">Volver al historial</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-12">
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4" />
            Error al cargar el incendio.
          </div>
        </div>
      </div>
    )
  }

  if (!fire) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-12 text-center">
          <p className="mb-4 text-lg font-semibold text-foreground">Incendio no encontrado.</p>
          <Button asChild variant="secondary">
            <Link to="/fires/history">Volver al historial</Link>
          </Button>
        </div>
      </div>
    )
  }

  const slides = fire.slides_data?.filter((slide) => slide.url) ?? []
  const protectedAreas = fire.protected_areas ?? []
  const uniqueProtectedAreas = (() => {
    const seen = new Set<string>()
    const result: typeof protectedAreas = []
    for (const area of protectedAreas) {
      const key = (area.name ?? '').trim().toLowerCase()
      if (!key) continue
      if (seen.has(key)) continue
      seen.add(key)
      result.push(area)
    }
    return result
  })()

  const infoCards = [
    {
      label: t('province'),
      value: fire.province || 'N/A',
      icon: MapPin,
    },
    {
      label: 'Fecha detectado',
      value: formatDate(fire.start_date),
      icon: Calendar,
    },
    {
      label: t('area'),
      value: formatHectares(fire.estimated_area_hectares),
      icon: Flame,
    },
    {
      label: 'Cantidad de veces detectado',
      value: fire.total_detections.toLocaleString('es-AR'),
      icon: Activity,
    },
  ]

  return (
    <div className="min-h-screen bg-background">
      <div className="relative">
        <div className="h-64 md:h-80">
          {mapFire ? (
            <Suspense fallback={mapFallback}>
              <FireMap
                fires={[mapFire]}
                selectedFire={mapFire}
                height="h-full"
                interactive={false}
                popupVariant="fire_detail"
              />
            </Suspense>
          ) : (
            mapFallback
          )}
        </div>
        <Button
          asChild
          variant="secondary"
          size="sm"
          className="absolute left-4 top-4 z-[1000] gap-2"
        >
          <Link to="/fires/history">
            <ArrowLeft className="h-4 w-4" />
            {t('fireHistory')}
          </Link>
        </Button>
      </div>

      <div className="container mx-auto px-4 py-6">
        {fire.processing_error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            {fire.processing_error}
          </div>
        )}

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {infoCards.map((card) => {
            const Icon = card.icon
            return (
              <Card key={card.label}>
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{card.label}</p>
                    <p className="font-semibold text-foreground">{card.value}</p>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        <div className="grid gap-6">
          {/* Carrusel de imágenes HD oculto temporalmente */}

          <div className="space-y-6">
            {isEpisodeDetail ? (
              <div className="rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                Calidad no disponible para episodios sin evento asociado.
              </div>
            ) : (
              <QualityIndicator quality={quality} isLoading={qualityLoading} error={qualityError} />
            )}

            <Card>
              <CardHeader className="flex items-center justify-between gap-2 sm:flex-row">
                <CardTitle>Áreas afectadas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                {fire.in_protected_area ? (
                  <div className="space-y-2">
                    {uniqueProtectedAreas.length ? (
                      <ul className="space-y-2">
                        {uniqueProtectedAreas.map((area) => (
                          <li key={area.id} className="rounded-lg border border-border bg-muted/40 p-3">
                            <p className="font-semibold text-foreground">{area.name}</p>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>El incendio intersecta un area protegida.</p>
                    )}
                    {fire.overlap_percentage !== null && fire.overlap_percentage !== undefined && (
                      <p>
                        Superficie afectada: {fire.overlap_percentage.toFixed(1)}%
                      </p>
                    )}
                  </div>
                ) : (
                  <p>No se detectaron areas protegidas asociadas.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Confianza promedio</p>
                <p className="font-semibold text-foreground">
                  {fire.avg_confidence !== null && fire.avg_confidence !== undefined
                    ? `${fire.avg_confidence.toFixed(1)}%`
                    : 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <Flame className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">FRP max</p>
                <p className="font-semibold text-foreground">
                  {fire.max_frp !== null && fire.max_frp !== undefined
                    ? fire.max_frp.toFixed(1)
                    : 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Coordenadas</p>
                <p className="text-sm font-semibold text-foreground">
                  {centroid
                    ? `${centroid.latitude.toFixed(4)}, ${centroid.longitude.toFixed(4)}`
                    : 'N/A'}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  )
}
