import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapPin, Calendar, Ruler, ArrowRight, Flame } from 'lucide-react'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Carousel,
  type CarouselApi,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from '@/components/ui/carousel'
import {
  formatDate,
  formatHectares,
  getSeverityConfig,
} from '@/types/fire'
import type { EpisodeListItem, EpisodeStatus } from '@/types/episode'
import { cn } from '@/lib/utils'

const STATUS_LABELS: Record<EpisodeStatus, string> = {
  active: 'Activo',
  monitoring: 'Monitoreo',
  extinct: 'Extinto',
  closed: 'Cerrado',
}

const STATUS_STYLES: Record<EpisodeStatus, string> = {
  active: 'border-red-200 bg-red-100 text-red-700',
  monitoring: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  extinct: 'border-slate-200 bg-slate-100 text-slate-600',
  closed: 'border-slate-200 bg-slate-100 text-slate-600',
}

function resolveStatus(episode: EpisodeListItem): EpisodeStatus {
  const status = episode.status
  if (status && status in STATUS_LABELS) {
    return status as EpisodeStatus
  }

  return 'extinct'
}

function buildEpisodeTitle(provinces?: string[] | null) {
  if (!provinces || provinces.length === 0) return 'Incendio sin provincia'
  if (provinces.length === 1) return `Incendio en ${provinces[0]}`
  return `Incendio en ${provinces[0]} (+${provinces.length - 1})`
}

interface FireCardProps {
  fire: EpisodeListItem
  slideStage?: number // 1: primer thumb, 2: segundo, 3: tercero
}

export function FireCard({ fire, slideStage = 3 }: FireCardProps) {
  const severity = getSeverityConfig(fire.frp_max)
  const title = buildEpisodeTitle(fire.provinces)
  const statusKey = resolveStatus(fire)
  const slides =
    fire.slides_data?.filter((slide) => slide.thumbnail_url || slide.url) ?? []
  const slidesToShow = slides.slice(0, Math.min(slides.length, slideStage))
  const [carouselApi, setCarouselApi] = useState<CarouselApi | null>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const detailId = fire.representative_event_id ?? fire.id

  useEffect(() => {
    if (!carouselApi) return

    const handleSelect = () => {
      setActiveIndex(carouselApi.selectedScrollSnap())
    }

    handleSelect()
    carouselApi.on('select', handleSelect)
    carouselApi.on('reInit', handleSelect)

    return () => {
      carouselApi.off('select', handleSelect)
      carouselApi.off('reInit', handleSelect)
    }
  }, [carouselApi])

  return (
    <Card className="overflow-hidden gap-0 p-0 transition-all hover:-translate-y-1 hover:shadow-lg">
      <div className="relative aspect-[4/3] overflow-hidden bg-gradient-to-br from-emerald-50 via-emerald-100/50 to-amber-50">
        {slidesToShow.length ? (
          <Carousel className="h-full w-full" setApi={setCarouselApi}>
            <CarouselContent className="h-full ml-0">
              {slidesToShow.map((slide, index) => {
                const slideUrl = slide.thumbnail_url ?? slide.url ?? ''
                return (
                  <CarouselItem key={`${slide.type}-${index}`} className="h-full pl-0">
                    <div className="relative h-full w-full">
                      <img
                        src={slideUrl}
                        alt={slide.type}
                        className="block h-full w-full object-cover"
                        loading="lazy"
                        decoding="async"
                        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                        />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/35 via-black/0 to-black/10" />
                      <div className="absolute bottom-2 left-2 rounded bg-black/40 px-2 py-1 text-xs font-medium text-white">
                        {slide.type.toUpperCase()}
                      </div>
                    </div>
                  </CarouselItem>
                )
              })}
            </CarouselContent>
            {slidesToShow.length > 1 && (
              <>
                <CarouselPrevious className="left-2 top-1/2 h-7 w-7 -translate-y-1/2 border-white/50 bg-white/80 text-emerald-700" />
                <CarouselNext className="right-2 top-1/2 h-7 w-7 -translate-y-1/2 border-white/50 bg-white/80 text-emerald-700" />
                <div className="absolute bottom-6 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-black/30 px-2 py-1 backdrop-blur-sm sm:hidden">
                  {slidesToShow.map((slide, index) => (
                    <button
                      key={`${slide.type}-${index}-dot`}
                      type="button"
                      onClick={() => carouselApi?.scrollTo(index)}
                      aria-label={`Ir a la diapositiva ${index + 1}`}
                      aria-current={index === activeIndex}
                      className={cn(
                        'h-2 w-2 rounded-full transition',
                        index === activeIndex ? 'bg-white' : 'bg-white/50',
                      )}
                    />
                  ))}
                </div>
              </>
            )}
          </Carousel>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 rounded-2xl bg-white/60 px-6 py-4 shadow-sm backdrop-blur-sm">
              <Flame className={cn('h-12 w-12', severity.iconColor)} />
              <span className="max-w-[180px] truncate text-sm font-medium text-slate-700">
                {fire.provinces?.[0] ?? 'Sin provincia'}
              </span>
            </div>
          </div>
        )}
      </div>

      <CardContent className="p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <h3 className="min-w-0 flex-1 line-clamp-2 text-lg font-semibold leading-tight text-foreground">
            {title}
          </h3>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge
              variant="outline"
              className={cn('border font-medium whitespace-nowrap', severity.badgeClasses)}
            >
              {severity.label}
            </Badge>
            <Badge
              variant="outline"
              className={cn('border font-medium whitespace-nowrap', STATUS_STYLES[statusKey])}
            >
              {STATUS_LABELS[statusKey]}
            </Badge>
            {fire.is_recent && (
              <Badge
                variant="outline"
                className="border-amber-200 bg-amber-50 text-amber-700 text-xs whitespace-nowrap"
              >
                Reciente
              </Badge>
            )}
            {slidesToShow.length === 0 && (
              <Badge
                variant="outline"
                className="border-slate-200 bg-slate-50 text-slate-500 text-xs whitespace-nowrap"
              >
                Imagen pendiente
              </Badge>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-emerald-600" />
            {fire.provinces?.[0] ?? 'Sin provincia'}
          </span>
          <span className="flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-emerald-600" />
            {formatDate(fire.start_date)}
          </span>
          <span className="flex items-center gap-1.5">
            <Ruler className="h-4 w-4 text-emerald-600" />
            {formatHectares(fire.estimated_area_hectares)}
          </span>
        </div>
      </CardContent>

      <CardFooter className="border-t border-border bg-muted/30 p-4">
        <Button asChild className="w-full gap-2 bg-emerald-500 text-white hover:bg-emerald-600">
          <Link to={`/fires/${detailId}`}>
            Ver detalles
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

export function FireCardSkeleton() {
  return (
    <Card className="overflow-hidden gap-0 p-0">
      <div className="aspect-[4/3] animate-pulse bg-muted" />
      <CardContent className="p-4">
        <div className="mb-3 h-6 w-3/4 animate-pulse rounded bg-muted" />
        <div className="flex flex-wrap gap-4">
          <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
          <div className="h-4 w-16 animate-pulse rounded bg-muted" />
        </div>
      </CardContent>
      <CardFooter className="border-t border-border bg-muted/30 p-4">
        <div className="h-10 w-full animate-pulse rounded bg-muted" />
      </CardFooter>
    </Card>
  )
}
