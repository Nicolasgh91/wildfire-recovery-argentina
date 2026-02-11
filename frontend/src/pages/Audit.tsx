import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useAuditMutation } from '@/hooks/mutations/useAudit'
import { searchAuditEpisodes } from '@/services/endpoints/audit-search'
import type { AuditFire, EvidenceThumbnail } from '@/types/audit'
import type { AuditSearchResponse } from '@/types/audit-search'

const AuditMap = lazy(() => import('@/components/audit-map').then((mod) => ({ default: mod.AuditMap })))

const mapFallback = (
  <div className="flex h-64 items-center justify-center rounded-lg bg-muted">
    <p className="text-sm text-muted-foreground">Cargando mapa...</p>
  </div>
)

type AuditFormValues = {
  search?: string
  search_type: 'address'
  radius_m: number
  lat?: string
  lon?: string
  cadastral_id?: string
}

const AREA_PRESETS = [
  { label: 'Alrededores (500 m)', value: 500 },
  { label: 'Zona (1 km)', value: 1000 },
  { label: 'Amplio (3 km)', value: 3000 },
]

const buildAuditSchema = (messages: {
  invalid: string
  outOfRange: string
}) =>
  z
    .object({
      search: z.string().trim().optional(),
      search_type: z.literal('address'),
      radius_m: z.number().min(100, { message: messages.outOfRange }).max(5000, { message: messages.outOfRange }),
      lat: z
        .string()
        .trim()
        .optional()
        .refine((val) => !val || !Number.isNaN(Number(val)), { message: messages.invalid })
        .refine((val) => !val || (Number(val) >= -90 && Number(val) <= 90), { message: messages.outOfRange }),
      lon: z
        .string()
        .trim()
        .optional()
        .refine((val) => !val || !Number.isNaN(Number(val)), { message: messages.invalid })
        .refine((val) => !val || (Number(val) >= -180 && Number(val) <= 180), { message: messages.outOfRange }),
      cadastral_id: z.string().trim().optional(),
    })


const formatDate = (value: string | null | undefined, locale: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale).format(date)
}


const getDurationDays = (startDate: string, endDate?: string | null) => {
  const start = new Date(startDate)
  const end = endDate ? new Date(endDate) : new Date()
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
  const diffMs = Math.max(end.getTime() - start.getTime(), 0)
  return Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}

const getRecoverySignal = (status?: string | null) => {
  const normalized = (status ?? '').toLowerCase()
  if (normalized === 'extinct' || normalized === 'extinguished') {
    return { label: 'Recuperación positiva', className: 'bg-emerald-100 text-emerald-800 border-emerald-200' }
  }
  if (normalized === 'monitoring') {
    return { label: 'Recuperación en monitoreo', className: 'bg-amber-100 text-amber-800 border-amber-200' }
  }
  return { label: 'Impacto activo', className: 'bg-rose-100 text-rose-800 border-rose-200' }
}

const getProtectedAreaLabel = (fire: AuditFire, fallback: string) => {
  const names = fire.protected_area_names ?? []
  if (fire.in_protected_area || names.length > 0) {
    return names.length > 0 ? names.join(', ') : fallback
  }
  return ''
}

export default function AuditPage() {
  const { t, language } = useI18n()
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [analysisPreset, setAnalysisPreset] = useState(1000)
  const [localError, setLocalError] = useState<string | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResult, setSearchResult] = useState<AuditSearchResponse | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10
  const locale = language === 'es' ? 'es-AR' : 'en-US'

  const schema = useMemo(
    () =>
      buildAuditSchema({
        invalid: t('invalidNumber'),
        outOfRange: t('outOfRange'),
      }),
    [t],
  )

  const form = useForm<AuditFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      search: '',
      search_type: 'address',
      radius_m: analysisPreset,
      lat: '',
      lon: '',
      cadastral_id: '',
    },
    mode: 'onChange',
  })

  useEffect(() => {
    form.setValue('radius_m', analysisPreset, { shouldDirty: true, shouldValidate: true })
  }, [analysisPreset, form])

  const auditMutation = useAuditMutation()
  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale, {
        maximumFractionDigits: 0,
      }),
    [locale],
  )

  const resolvePlaceTypeLabel = (type?: string | null) => {
    if (type === 'province') return t('placeTypeProvince')
    if (type === 'protected_area') return t('placeTypeProtectedArea')
    if (type === 'address') return t('placeTypeAddress')
    return type ?? '-'
  }

  const handleMapSelect = (latitude: number, longitude: number) => {
    form.setValue('lat', latitude.toFixed(6), { shouldDirty: true, shouldValidate: true })
    form.setValue('lon', longitude.toFixed(6), { shouldDirty: true, shouldValidate: true })
    setLocalError(null)
  }

  const handleSubmit = async (values: AuditFormValues) => {
    auditMutation.reset()
    setLocalError(null)
    setCurrentPage(1) // Resetear página al hacer nueva búsqueda
    if (!values.lat || !values.lon) {
      const query = values.search?.trim()
      if (!query) {
        setLocalError(t('noPointError'))
        return
      }

      setSearchLoading(true)
      setSearchResult(null)
      try {
        const response = await searchAuditEpisodes(query, {
          limit: 20,
          radius_km: (values.radius_m ?? analysisPreset) / 1000,
        })
        setSearchResult(response)
      } catch {
        setLocalError(t('geocodeNotFound'))
      } finally {
        setSearchLoading(false)
      }
      return
    }
    auditMutation.mutate({
      lat: Number(values.lat),
      lon: Number(values.lon),
      radius_meters: values.radius_m,
      cadastral_id: values.cadastral_id?.trim() || undefined,
      metadata: { is_test: import.meta.env.MODE === 'test' },
    })
  }

  const result = auditMutation.data

  // Lógica de paginación para episodios
  const paginatedEpisodes = useMemo(() => {
    if (!searchResult?.episodes) return []
    const startIndex = (currentPage - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    return searchResult.episodes.slice(startIndex, endIndex)
  }, [searchResult, currentPage])

  const totalPages = useMemo(() => {
    if (!searchResult?.episodes) return 0
    return Math.ceil(searchResult.episodes.length / itemsPerPage)
  }, [searchResult])

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const renderThumbnails = (thumbnails: EvidenceThumbnail[]) => {
    if (!thumbnails?.length) return null

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-foreground">{t('evidenceGallery')}</h3>
          <Badge variant="secondary">{thumbnails.length} imágenes</Badge>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {thumbnails.map((thumb) => {
            const dateLabel = formatDate(thumb.acquisition_date ?? thumb.fire_event_id, locale)
            const typeLabel = thumb.image_type ?? 'THUMB'
            return (
              <Card key={`${thumb.fire_event_id}-${thumb.thumbnail_url}`} className="overflow-hidden">
                <div className="aspect-video bg-muted">
                  <img
                    src={thumb.thumbnail_url}
                    alt={typeLabel}
                    className="h-full w-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                </div>
                <CardContent className="space-y-1 p-3">
                  <p className="text-sm font-semibold text-foreground">{dateLabel}</p>
                  <p className="text-xs text-muted-foreground">{typeLabel}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">{thumb.gee_system_index ?? ''}</span>
                    {isAuthenticated ? (
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-2"
                        asChild
                      >
                        <a href={thumb.thumbnail_url} download target="_blank" rel="noreferrer">
                          <Download className="h-4 w-4" />
                          {t('download')}
                        </a>
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-2"
                        onClick={() => navigate('/login')}
                      >
                        <Download className="h-4 w-4" />
                        {t('loginToDownload')}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-background">
      <div className="container mx-auto px-4 py-6">
        <div className="mb-6 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-3xl font-bold text-foreground">{t('verifyTerrain')}</h1>
              <p className="text-sm text-muted-foreground">{t('verifySubtitle')}</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">{t('verifyMicrocopyA')}</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2 lg:auto-rows-[minmax(0,1fr)]">
          {/* Mapa */}
          <div className="h-full">
            <div className="h-full min-h-[400px] w-full rounded-lg border border-border bg-muted/20 p-2">
              <Suspense fallback={mapFallback}>
                <AuditMap onLocationSelect={handleMapSelect} />
              </Suspense>
            </div>
          </div>

          {/* Panel derecho */}
          <Card className="flex h-full flex-col">
            <CardHeader>
              <CardTitle>{t('verifyTerrain')}</CardTitle>
              <CardDescription>{t('verifySubtitle')}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-4">
              <Form {...form}>
                <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
                  <div className="grid gap-3">
                    <FormField
                      control={form.control}
                      name="search"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('searchPlace')}</FormLabel>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder={t('searchPlaceholder')}
                              data-testid="search-place"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="space-y-2">
                    <FormLabel>{t('analysisArea')}</FormLabel>
                    <div className="flex flex-wrap gap-2">
                      {AREA_PRESETS.map((opt) => (
                        <Button
                          key={opt.value}
                          type="button"
                          variant={analysisPreset === opt.value ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setAnalysisPreset(opt.value)}
                        >
                          {opt.label}
                        </Button>
                      ))}
                    </div>
                  </div>

                  <Accordion type="single" collapsible>
                    <AccordionItem value="advanced">
                      <AccordionTrigger className="text-sm font-semibold">
                        {t('advancedOptions')}
                      </AccordionTrigger>
                      <AccordionContent className="space-y-4 pt-2">
                        <div className="grid gap-3 sm:grid-cols-2">
                          <FormField
                            control={form.control}
                            name="lat"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>{t('latitude')}</FormLabel>
                                <FormControl>
                                  <Input {...field} inputMode="decimal" placeholder="-38.4161" />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                          <FormField
                            control={form.control}
                            name="lon"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>{t('longitude')}</FormLabel>
                                <FormControl>
                                  <Input {...field} inputMode="decimal" placeholder="-63.6167" />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                        <FormField
                          control={form.control}
                          name="cadastral_id"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>{t('cadastralId')}</FormLabel>
                              <FormControl>
                                <Input {...field} placeholder="AR-0000-000000" />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="radius_m"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>{t('customRadius')}</FormLabel>
                              <FormControl>
                                <Input
                                  {...field}
                                  value={field.value ?? analysisPreset}
                                  onChange={(e) => field.onChange(Number(e.target.value))}
                                  inputMode="numeric"
                                  type="number"
                                  min={100}
                                  max={5000}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>

                  <Button
                    type="submit"
                    data-testid="audit-submit"
                  disabled={auditMutation.isPending || searchLoading || !form.formState.isValid}
                  className="w-full gap-2"
                >
                  {auditMutation.isPending || searchLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {searchLoading ? t('geocodeLoading') : t('loading')}
                    </>
                  ) : (
                      <>
                        <Search className="h-4 w-4" />
                        {t('verifyCTA')}
                      </>
                    )}
                  </Button>
                  <p className="text-xs text-muted-foreground">{t('verifyMicrocopyB')}</p>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>

        <div className="mt-6">
          <Card className="flex flex-col">
            <CardHeader>
              <CardTitle>{t('results')}</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 space-y-4 overflow-y-auto">
              {searchLoading && (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    {t('auditSearchLoading')}
                  </div>
                </div>
              )}

              {searchResult && !searchLoading && (
                <div className="space-y-4 rounded-lg border border-border bg-muted/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">{t('resolvedPlace')}</p>
                      <p className="text-sm font-semibold text-foreground">
                        {searchResult.resolved_place.label}
                      </p>
                    </div>
                    <Badge variant="secondary">
                      {resolvePlaceTypeLabel(searchResult.resolved_place.type)}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span>
                      {t('episodesFound')}: {searchResult.total}
                    </span>
                    {searchResult.date_range?.earliest && (
                      <span>
                        {t('dateRange')}:{' '}
                        {formatDate(searchResult.date_range.earliest, locale)} a{' '}
                        {formatDate(searchResult.date_range.latest ?? null, locale)}
                      </span>
                    )}
                  </div>

                  {searchResult.episodes.length === 0 ? (
                    <p className="text-sm text-muted-foreground">{t('auditSearchEmpty')}</p>
                  ) : (
                    <div className="space-y-4">
                      <div className="w-full overflow-x-auto rounded-md border">
                        <Table className="min-w-[980px]">
                          <TableHeader>
                            <TableRow>
                              <TableHead className="whitespace-nowrap">{t('date')}</TableHead>
                              <TableHead className="whitespace-nowrap">{t('status')}</TableHead>
                              <TableHead className="whitespace-nowrap">{t('province')}</TableHead>
                              <TableHead className="whitespace-nowrap">Duración (días)</TableHead>
                              <TableHead className="whitespace-nowrap">FRP máx</TableHead>
                              <TableHead className="whitespace-nowrap">{t('area')}</TableHead>
                              <TableHead className="whitespace-nowrap">{t('detections')}</TableHead>
                              <TableHead className="whitespace-nowrap">Señal de recuperación</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {paginatedEpisodes.map((episode) => {
                              const durationDays = getDurationDays(episode.start_date, episode.end_date)
                              const recoverySignal = getRecoverySignal(episode.status)

                              return (
                                <TableRow key={episode.id}>
                                  <TableCell>
                                    {formatDate(episode.start_date, locale)}
                                    {episode.end_date ? ` a ${formatDate(episode.end_date, locale)}` : ''}
                                  </TableCell>
                                  <TableCell>{episode.status ?? '-'}</TableCell>
                                  <TableCell>{episode.provinces?.[0] ?? '-'}</TableCell>
                                  <TableCell>{durationDays ? numberFormatter.format(durationDays) : '-'}</TableCell>
                                  <TableCell>
                                    {episode.frp_max
                                      ? numberFormatter.format(Math.round(episode.frp_max))
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    {episode.estimated_area_hectares
                                      ? `${numberFormatter.format(Math.round(episode.estimated_area_hectares))} ha`
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    {episode.detection_count
                                      ? numberFormatter.format(episode.detection_count)
                                      : '-'}
                                  </TableCell>
                                  <TableCell>
                                    <Badge className={`border ${recoverySignal.className}`}>{recoverySignal.label}</Badge>
                                  </TableCell>
                                </TableRow>
                              )
                            })}
                          </TableBody>
                        </Table>
                      </div>

                      {/* Controles de paginación */}
                      {totalPages > 1 && (
                        <div className="flex items-center justify-between pt-4">
                          <div className="text-sm text-muted-foreground">
                            Mostrando {((currentPage - 1) * itemsPerPage) + 1} a {Math.min(currentPage * itemsPerPage, searchResult.episodes.length)} de {searchResult.episodes.length} resultados
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handlePageChange(currentPage - 1)}
                              disabled={currentPage === 1}
                              className="gap-1"
                            >
                              <ChevronLeft className="h-4 w-4" />
                              Anterior
                            </Button>
                            <span className="text-sm text-muted-foreground px-2">
                              Página {currentPage} de {totalPages}
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handlePageChange(currentPage + 1)}
                              disabled={currentPage === totalPages}
                              className="gap-1"
                            >
                              Siguiente
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {!result && !auditMutation.isPending && !auditMutation.error && !localError && (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <p className="font-semibold text-foreground">{t('whatYouWillSee')}</p>
                  <ul className="space-y-1">
                    <li>• {t('seeTimeline')}</li>
                    <li>• {t('seeVegetation')}</li>
                    <li>• {t('seeGallery')}</li>
                    <li>• {t('seeSignals')}</li>
                  </ul>
                  <p className="text-xs text-muted-foreground">{t('emptyHint')}</p>
                </div>
              )}

              {auditMutation.isPending && (
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    {t('loadingFires')}
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    {t('loadingVegetation')}
                  </div>
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    {t('loadingEvidence')}
                  </div>
                </div>
              )}

              {localError && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-5 w-5" />
                  <AlertTitle>{t('errorTitle')}</AlertTitle>
                  <AlertDescription>{localError}</AlertDescription>
                  <CardFooter className="mt-2 px-0">
                    <Button variant="outline" size="sm" onClick={() => setLocalError(null)}>
                      {t('retry')}
                    </Button>
                  </CardFooter>
                </Alert>
              )}

              {auditMutation.error && !localError && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-5 w-5" />
                  <AlertTitle>{t('errorTitle')}</AlertTitle>
                  <AlertDescription>
                    {form.getValues('lat') && form.getValues('lon')
                      ? t('technicalError')
                      : t('noPointError')}
                  </AlertDescription>
                  <CardFooter className="mt-2 px-0">
                    <Button variant="outline" size="sm" onClick={() => auditMutation.reset()}>
                      {t('retry')}
                    </Button>
                  </CardFooter>
                </Alert>
              )}

              {result && !auditMutation.isPending && (
                <div className="space-y-6">
                  {result.is_prohibited ? (
                    <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
                      <AlertTriangle className="h-5 w-5" />
                      <AlertTitle className="text-lg font-semibold">
                        {t('constructionProhibited')}
                      </AlertTitle>
                      <AlertDescription className="mt-2">
                        <p className="mb-2">
                          {t('firesFound')}: {result.fires_found}
                        </p>
                        {result.prohibition_until && (
                          <p className="font-semibold">
                            {t('prohibitedUntil')}: {formatDate(result.prohibition_until, locale)}
                          </p>
                        )}
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert className="border-primary/50 bg-primary/10">
                      <CheckCircle2 className="h-5 w-5 text-primary" />
                      <AlertTitle className="text-lg font-semibold text-primary">
                        {t('noRestrictionsFound')}
                      </AlertTitle>
                      <AlertDescription className="mt-2 text-foreground">
                        {t('firesFound')}: {result.fires_found}
                      </AlertDescription>
                    </Alert>
                  )}

                  {result.fires.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-lg font-semibold text-foreground">{t('firesFound')}</h3>
                      <div className="space-y-3">
                        {result.fires.map((fire) => {
                          const protectedLabel = getProtectedAreaLabel(fire, t('protectedArea'))
                          const protectedBadge =
                            protectedLabel || (fire.in_protected_area ? t('protectedArea') : '')
                          return (
                            <div key={fire.fire_event_id} className="rounded-lg border border-border p-3">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-foreground">
                                  {formatDate(fire.fire_date, locale)}
                                </p>
                                {protectedBadge ? (
                                  <Badge variant="secondary">{protectedBadge}</Badge>
                                ) : null}
                              </div>
                              <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                                <span>
                                  {t('province')}: {fire.province ?? '-'}
                                </span>
                                <span>
                                  {t('distanceMeters')}: {numberFormatter.format(Math.round(fire.distance_meters))} m
                                </span>
                                {fire.prohibition_until && (
                                  <span>
                                    {t('prohibitedUntil')}: {formatDate(fire.prohibition_until, locale)}
                                  </span>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {renderThumbnails(result.evidence?.thumbnails ?? [])}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
