import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  BarChart3,
  Calendar,
  Filter,
  Flame,
  Loader2,
  MapPin,
  ShieldCheck,
  Table2,
} from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis, ResponsiveContainer } from 'recharts'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { FireFilters } from '@/components/fires/fire-filters'
import { Pagination } from '@/components/fires/pagination'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import { useIsMobile } from '@/hooks/use-mobile'
import { useFires } from '@/hooks/queries/useFires'
import { usePrefetchFire } from '@/hooks/queries/useFire'
import { useFireStats } from '@/hooks/queries/useFireStats'
import { FireHistorySkeleton } from '@/components/fires/FireHistorySkeleton'
import {
  formatDate,
  formatHectares,
  type FireFiltersState,
  type FireSortValue,
} from '@/types/fire'
import { FireCardSkeleton } from '@/components/FireCardSkeleton'
import { useExportMutation } from '@/hooks/mutations/useExportMutation'
import { getFires } from '@/services/endpoints/fires'
import { queryKeys } from '@/lib/queryClient'

const DEFAULT_PAGE_SIZE = 20
const ROW_HEIGHT_PX = 48
const ROW_OVERSCAN = 8

const getResponsivePageSize = () => DEFAULT_PAGE_SIZE

const DEFAULT_FILTERS: FireFiltersState = {
  province: '',
  status_scope: 'historical',
  date_from: '',
  date_to: '',
  search: '',
  sort_by: 'start_date_desc',
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
}

const PAGE_SIZE_OPTIONS = [20, 30, 50, 100]

const SORT_CONFIG: Record<FireSortValue, { sortBy: string; sortDesc: boolean }> = {
  start_date_desc: { sortBy: 'start_date', sortDesc: true },
  start_date_asc: { sortBy: 'start_date', sortDesc: false },
  area_desc: { sortBy: 'estimated_area_hectares', sortDesc: true },
  area_asc: { sortBy: 'estimated_area_hectares', sortDesc: false },
  frp_desc: { sortBy: 'max_frp', sortDesc: true },
  frp_asc: { sortBy: 'max_frp', sortDesc: false },
}

const isSortValue = (value: string | null): value is FireSortValue =>
  value !== null && value in SORT_CONFIG

const parseNumber = (value: string | null, fallback: number): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

const parsePageSize = (value: string | null, fallback: number): number => {
  const parsed = parseNumber(value, fallback)
  return PAGE_SIZE_OPTIONS.includes(parsed) ? parsed : fallback
}

const normalizeDate = (value: string): string => {
  const trimmed = value.trim()
  return /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? trimmed : ''
}

const parseFilters = (searchParams: URLSearchParams): FireFiltersState => {
  const sortValue = searchParams.get('sort_by')
  const statusScopeParam = searchParams.get('status_scope')
  const fallbackPageSize = getResponsivePageSize()

  return {
    province: searchParams.get('province') || '',
    status_scope:
      statusScopeParam === 'active' ||
      statusScopeParam === 'historical' ||
      statusScopeParam === 'all'
        ? statusScopeParam
        : DEFAULT_FILTERS.status_scope,
    date_from: searchParams.get('date_from') || '',
    date_to: searchParams.get('date_to') || '',
    search: searchParams.get('search') || '',
    sort_by: isSortValue(sortValue) ? sortValue : DEFAULT_FILTERS.sort_by,
    page: parseNumber(searchParams.get('page'), DEFAULT_FILTERS.page),
    page_size: parsePageSize(searchParams.get('page_size'), fallbackPageSize),
  }
}

const buildSearchParams = (filters: FireFiltersState): URLSearchParams => {
  const params = new URLSearchParams()
  const dateFrom = normalizeDate(filters.date_from)
  const dateTo = normalizeDate(filters.date_to)

  if (filters.province) params.set('province', filters.province)
  if (filters.status_scope) params.set('status_scope', filters.status_scope)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (filters.search) params.set('search', filters.search)
  if (filters.sort_by) params.set('sort_by', filters.sort_by)

  params.set('page', filters.page.toString())
  params.set('page_size', filters.page_size.toString())

  return params
}

const buildApiParams = (filters: FireFiltersState): URLSearchParams => {
  const params = new URLSearchParams()
  const searchValue = filters.search.trim()
  const dateFrom = normalizeDate(filters.date_from)
  const dateTo = normalizeDate(filters.date_to)

  if (filters.province) params.set('province', filters.province)
  if (filters.status_scope === 'active') params.set('status_scope', 'active')
  if (filters.status_scope === 'historical') params.set('status_scope', 'historical')
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (searchValue.length >= 2) params.set('search', searchValue)

  const sort = SORT_CONFIG[filters.sort_by] || SORT_CONFIG.start_date_desc
  params.set('sort_by', sort.sortBy)
  params.set('sort_desc', sort.sortDesc ? 'true' : 'false')
  params.set('page', filters.page.toString())
  params.set('page_size', filters.page_size.toString())

  return params
}

const buildStatsParams = (filters: FireFiltersState): URLSearchParams => {
  const params = new URLSearchParams()
  const dateFrom = normalizeDate(filters.date_from)
  const dateTo = normalizeDate(filters.date_to)
  if (filters.province) params.set('province', filters.province)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return params
}

const buildExportParams = (filters: FireFiltersState): URLSearchParams => {
  const params = new URLSearchParams()
  const searchValue = filters.search.trim()
  const dateFrom = normalizeDate(filters.date_from)
  const dateTo = normalizeDate(filters.date_to)

  if (filters.province) params.set('province', filters.province)
  if (filters.status_scope === 'active') params.set('status_scope', 'active')
  if (filters.status_scope === 'historical') params.set('status_scope', 'historical')
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (searchValue.length >= 2) params.set('search', searchValue)

  params.set('format', 'csv')

  return params
}

const paramsToObject = (params: URLSearchParams): Record<string, string> =>
  Object.fromEntries(params.entries())

const formatNumber = (value: number | null | undefined) =>
  new Intl.NumberFormat('es-AR').format(value ?? 0)

const formatPercent = (value: number | null | undefined) =>
  value === null || value === undefined ? 'N/A' : `${value.toFixed(1)}%`

const formatDuration = (value: number | null | undefined) =>
  value === null || value === undefined ? 'N/A' : `${value.toFixed(1)} h`

const formatDelta = (metric?: { delta: number; delta_pct?: number | null }) => {
  if (!metric) return '—'
  const sign = metric.delta > 0 ? '+' : metric.delta < 0 ? '' : ''
  const pct =
    metric.delta_pct === null || metric.delta_pct === undefined
      ? 'N/A'
      : `${metric.delta_pct.toFixed(1)}%`
  return `${sign}${metric.delta.toFixed(0)} (${pct})`
}

const statusBadgeClasses: Record<string, string> = {
  active: 'border-red-200 bg-red-100 text-red-700',
  controlled: 'border-amber-200 bg-amber-100 text-amber-700',
  monitoring: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  extinguished: 'border-slate-200 bg-slate-100 text-slate-700',
}

const statusLabel: Record<string, string> = {
  active: 'Activo',
  controlled: 'Controlado',
  monitoring: 'Monitoreo',
  extinguished: 'Extinguido',
}

const chartConfig = {
  fires: { label: 'Incendios', color: 'hsl(153 47% 40%)' },
  provinces: { label: 'Provincias', color: 'hsl(32 89% 55%)' },
  frp: { label: 'FRP max', color: 'hsl(0 84% 60%)' },
}

type FireRowDto = {
  id: string
  start_date: string
  end_date?: string | null
  duration_hours?: number | null
  province?: string | null
  department?: string | null
  status?: string
  estimated_area_hectares?: number | null
  total_detections: number
  max_frp?: number | null
  avg_confidence?: number | null
  is_significant: boolean
  in_protected_area: boolean
  protected_area_name?: string | null
  overlap_percentage?: number | null
  count_protected_areas?: number | null
  has_satellite_imagery: boolean
  centroid?: { latitude: number; longitude: number } | null
}

type FireRowProps = {
  row: FireRowDto
  showAdvancedColumns: boolean
  showCoordinates: boolean
  onHover: (id: string) => void
}

const FireRow = memo(({ row, showAdvancedColumns, showCoordinates, onHover }: FireRowProps) => {
  const statusKey = row.status || 'extinguished'
  const statusText = statusLabel[statusKey] || statusKey
  const statusClass = statusBadgeClasses[statusKey] || statusBadgeClasses.extinguished
  const countAreas = row.count_protected_areas ?? 0
  const areaCountBadge = countAreas > 1 ? 'border-amber-200 bg-amber-100 text-amber-700' : undefined

  return (
    <TableRow onMouseEnter={() => onHover(row.id)}>
      <TableCell className="font-mono text-xs">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger className="cursor-pointer">{row.id.slice(0, 8)}</TooltipTrigger>
            <TooltipContent>{row.id}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </TableCell>
      <TableCell>{formatDate(row.start_date)}</TableCell>
      {showAdvancedColumns && (
        <TableCell className="hidden lg:table-cell">{formatDate(row.end_date)}</TableCell>
      )}
      {showAdvancedColumns && (
        <TableCell className="hidden lg:table-cell">{formatDuration(row.duration_hours)}</TableCell>
      )}
      <TableCell>{row.province || '—'}</TableCell>
      {showAdvancedColumns && (
        <TableCell className="hidden lg:table-cell max-w-[160px] truncate">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger className="block max-w-[160px] truncate text-left">
                {row.department || '—'}
              </TooltipTrigger>
              {row.department && <TooltipContent>{row.department}</TooltipContent>}
            </Tooltip>
          </TooltipProvider>
        </TableCell>
      )}
      <TableCell>
        <Badge variant="outline" className={cn('border', statusClass)}>
          {statusText}
        </Badge>
      </TableCell>
      <TableCell>{formatHectares(row.estimated_area_hectares)}</TableCell>
      {showAdvancedColumns && (
        <TableCell className="hidden xl:table-cell">{formatNumber(row.total_detections)}</TableCell>
      )}
      {showAdvancedColumns && (
        <TableCell className="hidden xl:table-cell">
          {row.max_frp !== null && row.max_frp !== undefined ? row.max_frp.toFixed(1) : '—'}
        </TableCell>
      )}
      {showAdvancedColumns && (
        <TableCell className="hidden xl:table-cell">
          {row.avg_confidence !== null && row.avg_confidence !== undefined
            ? `${row.avg_confidence.toFixed(1)}%`
            : '—'}
        </TableCell>
      )}
      {showAdvancedColumns && (
        <TableCell className="hidden lg:table-cell">
          <Badge variant={row.is_significant ? 'default' : 'outline'}>
            {row.is_significant ? 'Si' : 'No'}
          </Badge>
        </TableCell>
      )}
      <TableCell className="hidden lg:table-cell">
        <Badge variant={row.in_protected_area ? 'default' : 'outline'}>
          {row.in_protected_area ? 'Si' : 'No'}
        </Badge>
      </TableCell>
      {showAdvancedColumns && (
        <TableCell className="hidden xl:table-cell max-w-[180px] truncate">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger className="block max-w-[180px] truncate text-left">
                {row.protected_area_name || '—'}
              </TooltipTrigger>
              {row.protected_area_name && <TooltipContent>{row.protected_area_name}</TooltipContent>}
            </Tooltip>
          </TooltipProvider>
        </TableCell>
      )}
      <TableCell>{formatPercent(row.overlap_percentage)}</TableCell>
      <TableCell>
        <Badge variant="outline" className={areaCountBadge}>
          {countAreas || '—'}
        </Badge>
      </TableCell>
      {showAdvancedColumns && (
        <TableCell className="hidden lg:table-cell">
          <Badge variant={row.has_satellite_imagery ? 'default' : 'outline'}>
            {row.has_satellite_imagery ? 'Si' : 'No'}
          </Badge>
        </TableCell>
      )}
      {showCoordinates && (
        <TableCell className="hidden xl:table-cell">
          {row.centroid
            ? `${row.centroid.latitude.toFixed(3)}, ${row.centroid.longitude.toFixed(3)}`
            : '—'}
        </TableCell>
      )}
    </TableRow>
  )
})

export default function FireHistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const isMobile = useIsMobile()
  const filters = useMemo(() => parseFilters(searchParams), [searchParams])
  const prefetchFire = usePrefetchFire()
  const exportMutation = useExportMutation('incendios_historicos')
  const [showCoordinates, setShowCoordinates] = useState(false)
  const [showAdvancedColumns, setShowAdvancedColumns] = useState(false)
  const queryClient = useQueryClient()
  const tableContainerRef = useRef<HTMLDivElement | null>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(600)

  const effectivePageSize = useMemo(() => {
    const capped = Math.min(filters.page_size, 100)
    return isMobile ? Math.min(capped, 50) : capped
  }, [filters.page_size, isMobile])

  const listFilters = useMemo(
    () => paramsToObject(buildApiParams({ ...filters, page_size: effectivePageSize })),
    [effectivePageSize, filters]
  )

  const statsFilters = useMemo(() => paramsToObject(buildStatsParams(filters)), [filters])

  const {
    data,
    isLoading,
    isFetching,
    error,
  } = useFires(listFilters)

  const { data: stats, error: statsError } = useFireStats(statsFilters)

  const updateFilters = useCallback(
    (updates: Partial<FireFiltersState>) => {
      const nextFilters = { ...filters, ...updates }
      setSearchParams(buildSearchParams(nextFilters), { replace: false })
    },
    [filters, setSearchParams]
  )

  const handleExportCSV = useCallback(async () => {
    const exportParams = paramsToObject(buildExportParams(filters))
    try {
      const result = await exportMutation.mutateAsync(exportParams)
      if (!(result instanceof Blob)) {
        console.info(result?.message || 'Export scheduled')
      }
    } catch (err) {
      console.error('Export error:', err)
    }
  }, [exportMutation, filters])

  const handlePageChange = (page: number) => {
    updateFilters({ page })
  }

  const handlePageSizeChange = (pageSize: number) => {
    const capped = Math.min(pageSize, 100)
    const nextSize = isMobile ? Math.min(capped, 50) : capped
    updateFilters({ page_size: nextSize, page: 1 })
  }

  const listErrorMessage = error
    ? error instanceof Error
      ? error.message
      : 'Error al cargar los incendios'
    : null
  const statsErrorMessage = statsError
    ? statsError instanceof Error
      ? statsError.message
      : 'Error al cargar estadisticas'
    : null
  const showInitialSkeleton = isLoading && !data

  const fires = data?.fires ?? []
  const pagination = data?.pagination
  const statsPayload = stats?.stats
  const ytd = stats?.ytd_comparison
  const tableColumnCount = useMemo(() => {
    let count = 7 // id, inicio, provincia, estado, area, % afectado, areas
    count += showAdvancedColumns ? 8 : 0 // fin, duracion, depto, detecciones, frp, confianza, significativo, imagenes
    count += 1 // en area protegida
    count += showAdvancedColumns ? 1 : 0 // area protegida nombre
    count += showCoordinates ? 1 : 0 // coords
    return count
  }, [showAdvancedColumns, showCoordinates])
  const skeletonRows = useMemo(
    () => Array.from({ length: Math.min(effectivePageSize, 10) }),
    [effectivePageSize]
  )

  const provincesChartData = useMemo(() => {
    if (!statsPayload) return []
    return [...statsPayload.by_province]
      .sort((a, b) => b.fire_count - a.fire_count)
      .slice(0, 8)
      .map((item) => ({ name: item.name, fires: item.fire_count }))
  }, [statsPayload])

  const monthlyChartData = useMemo(() => {
    if (!statsPayload) return []
    return Object.entries(statsPayload.by_month)
      .map(([month, count]) => ({ month, fires: count }))
      .sort((a, b) => a.month.localeCompare(b.month))
  }, [statsPayload])

  const topFrpData = useMemo(() => {
    if (!statsPayload) return []
    return statsPayload.top_frp_fires.map((item) => ({
      name: (item.province || '').trim() || (item.id ? item.id.slice(0, 6) : 'Sin nombre'),
      fullName: item.province || item.id,
      frp: item.max_frp ?? 0,
    }))
  }, [statsPayload])

  const tableRows = useMemo(
    () =>
      fires.map((fire) => ({
        id: fire.id,
        start_date: fire.start_date,
        end_date: fire.end_date,
        duration_hours: fire.duration_hours,
        province: fire.province,
        department: fire.department,
        status: fire.status,
        estimated_area_hectares: fire.estimated_area_hectares,
        total_detections: fire.total_detections,
        max_frp: fire.max_frp,
        avg_confidence: fire.avg_confidence,
        is_significant: fire.is_significant,
        in_protected_area: fire.in_protected_area,
        protected_area_name: fire.protected_area_name,
        overlap_percentage: fire.overlap_percentage,
        count_protected_areas: fire.count_protected_areas,
        has_satellite_imagery: fire.has_satellite_imagery,
        centroid: fire.centroid,
      })),
    [fires]
  )

  const handleTableScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop)
  }, [])

  useEffect(() => {
    const node = tableContainerRef.current
    if (!node) return

    const measure = () => {
      setContainerHeight(node.clientHeight || 600)
    }

    measure()
    const resizeObserver = new ResizeObserver(measure)
    resizeObserver.observe(node)
    return () => resizeObserver.disconnect()
  }, [])

  const totalRows = tableRows.length
  const { startIndex, endIndex, paddingTop, paddingBottom } = useMemo(() => {
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT_PX) + ROW_OVERSCAN * 2
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT_PX) - ROW_OVERSCAN)
    const end = Math.min(totalRows, start + visibleCount)
    return {
      startIndex: start,
      endIndex: end,
      paddingTop: start * ROW_HEIGHT_PX,
      paddingBottom: Math.max(0, (totalRows - end) * ROW_HEIGHT_PX),
    }
  }, [containerHeight, scrollTop, totalRows])

  const visibleRows = useMemo(() => tableRows.slice(startIndex, endIndex), [tableRows, startIndex, endIndex])

  useEffect(() => {
    const paginationMeta = data?.pagination
    if (!paginationMeta) return
    const { page, total_pages } = paginationMeta
    if (page >= total_pages) return

    const nextFilters = paramsToObject(
      buildApiParams({ ...filters, page: page + 1, page_size: effectivePageSize })
    )

    queryClient.prefetchQuery({
      queryKey: queryKeys.fires.list(nextFilters),
      queryFn: ({ signal }) => getFires(nextFilters, signal),
      staleTime: 5 * 60 * 1000,
      cacheTime: 30 * 60 * 1000,
    })
  }, [data?.pagination, effectivePageSize, filters, queryClient])

  if (showInitialSkeleton) {
    return <FireHistorySkeleton />
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6">
        <div className="mb-6" />

        <div className="mb-8 space-y-6">
          {statsErrorMessage && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              {statsErrorMessage}
            </div>
          )}
          <div className="flex gap-4 overflow-x-auto pb-2 sm:grid sm:grid-cols-2 xl:grid-cols-3">
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total incendios
                </CardTitle>
                <Flame className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload ? formatNumber(statsPayload.total_fires) : '—'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {statsPayload
                    ? `${formatNumber(statsPayload.active_fires)} activos`
                    : 'Actualizando'}
                </p>
                {ytd?.total_fires && (
                  <p className="text-xs text-muted-foreground">YTD {formatDelta(ytd.total_fires)}</p>
                )}
              </CardContent>
            </Card>
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Activos vs Historicos
                </CardTitle>
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload
                    ? `${formatNumber(statsPayload.active_fires)} / ${formatNumber(
                        statsPayload.historical_fires
                      )}`
                    : '—'}
                </div>
                <p className="text-xs text-muted-foreground">Activos / Historicos</p>
              </CardContent>
            </Card>
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Hectareas quemadas
                </CardTitle>
                <MapPin className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload ? formatHectares(statsPayload.total_hectares) : '—'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Prom: {statsPayload ? formatHectares(statsPayload.avg_hectares) : '—'}
                </p>
                {ytd?.total_hectares && (
                  <p className="text-xs text-muted-foreground">YTD {formatDelta(ytd.total_hectares)}</p>
                )}
              </CardContent>
            </Card>
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Mediana de area
                </CardTitle>
                <Calendar className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload ? formatHectares(statsPayload.median_hectares) : '—'}
                </div>
                <p className="text-xs text-muted-foreground">En el periodo seleccionado</p>
              </CardContent>
            </Card>
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Areas protegidas
                </CardTitle>
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload ? formatNumber(statsPayload.fires_in_protected) : '—'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {statsPayload ? formatPercent(statsPayload.protected_percentage) : '—'} del total
                </p>
              </CardContent>
            </Card>
            <Card className="min-w-[220px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Incendios significativos
                </CardTitle>
                <Flame className="h-4 w-4 text-emerald-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">
                  {statsPayload ? formatNumber(statsPayload.significant_fires) : '—'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {statsPayload ? formatPercent(statsPayload.significant_percentage) : '—'} del total
                </p>
                {ytd?.significant_fires && (
                  <p className="text-xs text-muted-foreground">
                    YTD {formatDelta(ytd.significant_fires)}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="lg:hidden">
            <Tabs defaultValue="serie">
              <TabsList className="w-full">
                <TabsTrigger value="serie" className="flex-1">
                  Serie temporal
                </TabsTrigger>
                <TabsTrigger value="provincias" className="flex-1">
                  Provincias
                </TabsTrigger>
                <TabsTrigger value="frp" className="flex-1">
                  Top FRP
                </TabsTrigger>
              </TabsList>
              <TabsContent value="serie">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Serie temporal mensual</CardTitle>
                    <p className="text-sm text-muted-foreground">Cantidad de incendios por mes</p>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={chartConfig}>
                      <AreaChart data={monthlyChartData}>
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis dataKey="month" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} />
                        <ChartTooltip content={<ChartTooltipContent />} />
                        <Area
                          type="monotone"
                          dataKey="fires"
                          stroke="var(--color-fires)"
                          fill="var(--color-fires)"
                          fillOpacity={0.2}
                        />
                      </AreaChart>
                    </ChartContainer>
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="provincias">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Top provincias</CardTitle>
                    <p className="text-sm text-muted-foreground">Mayor cantidad de incendios</p>
                  </CardHeader>
                  <CardContent className="w-full overflow-hidden">
                    <ChartContainer config={chartConfig} className="h-56 w-full overflow-hidden">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={provincesChartData}
                          margin={{ top: 8, right: 8, left: 8, bottom: 12 }}
                        barSize={26}
                      >
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                        <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                        <ChartTooltip
                          content={<ChartTooltipContent />}
                          formatter={(val: number) => val.toFixed(1)}
                          labelFormatter={(label: string, payload) =>
                            (payload?.[0]?.payload?.name as string) || label
                          }
                        />
                        <Bar
                          dataKey="fires"
                          fill="var(--color-provinces)"
                          radius={[4, 4, 0, 0]}
                          label={{ position: 'top', formatter: (v: number) => v.toFixed(0), fontSize: 10 }}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </CardContent>
              </Card>
              </TabsContent>
              <TabsContent value="frp">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Top 10 por FRP</CardTitle>
                    <p className="text-sm text-muted-foreground">Poder radiativo maximo</p>
                  </CardHeader>
                  <CardContent className="w-full overflow-hidden">
                    <ChartContainer config={chartConfig} className="h-56 w-full overflow-hidden">
                      <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={topFrpData}
                        margin={{ top: 8, right: 8, left: 8, bottom: 12 }}
                        barSize={24}
                      >
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis
                          dataKey="name"
                          tickLine={false}
                          axisLine={false}
                          tick={{ fontSize: 10 }}
                          tickFormatter={(v: string) => (v && v.length > 10 ? `${v.slice(0, 9)}…` : v)}
                        />
                        <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                        <ChartTooltip
                          content={<ChartTooltipContent />}
                          formatter={(val: number) => val.toFixed(1)}
                          labelFormatter={(label: string, payload) =>
                            (payload?.[0]?.payload?.fullName as string) || label
                          }
                        />
                        <Bar
                          dataKey="frp"
                          fill="var(--color-frp)"
                          radius={[4, 4, 0, 0]}
                          label={{ position: 'top', formatter: (v: number) => v.toFixed(0), fontSize: 10 }}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          <div className="hidden gap-6 lg:grid lg:grid-cols-3 items-start">
            <Card className="min-w-0">
              <CardHeader className="flex items-center justify-between gap-2 sm:flex-row">
                <div>
                  <CardTitle className="text-base">Serie temporal mensual</CardTitle>
                  <p className="text-sm text-muted-foreground">Cantidad de incendios por mes</p>
                </div>
              </CardHeader>
              <CardContent className="w-full overflow-hidden">
                <ChartContainer config={chartConfig} className="h-72 w-full overflow-hidden">
                  <AreaChart data={monthlyChartData}>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" />
                    <XAxis dataKey="month" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Area
                      type="monotone"
                      dataKey="fires"
                      stroke="var(--color-fires)"
                      fill="var(--color-fires)"
                      fillOpacity={0.2}
                    />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>
            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-base">Top provincias</CardTitle>
                <p className="text-sm text-muted-foreground">Mayor cantidad de incendios</p>
              </CardHeader>
              <CardContent className="w-full overflow-hidden">
                <ChartContainer config={chartConfig} className="h-72 w-full overflow-hidden">
                  <BarChart data={provincesChartData} margin={{ top: 8, right: 8, left: 8, bottom: 16 }}>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: string) => (v && v.length > 12 ? `${v.slice(0, 11)}…` : v)}
                    />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip
                      content={<ChartTooltipContent />}
                      labelFormatter={(label: string, payload) => (payload?.[0]?.payload?.name as string) || label}
                    />
                    <Bar
                      dataKey="fires"
                      fill="var(--color-provinces)"
                      radius={[4, 4, 0, 0]}
                      label={{ position: 'top', formatter: (v: number) => v.toFixed(0), fontSize: 11 }}
                    />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>
            <Card className="min-w-0">
              <CardHeader className="flex items-center justify-between gap-2 sm:flex-row">
                <div>
                  <CardTitle className="text-base">Top 10 por FRP</CardTitle>
                  <p className="text-sm text-muted-foreground">Poder radiativo maximo</p>
                </div>
              </CardHeader>
              <CardContent className="w-full overflow-hidden">
                <ChartContainer config={chartConfig} className="h-72 w-full overflow-hidden">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topFrpData} margin={{ top: 8, right: 8, left: 8, bottom: 12 }} barSize={28}>
                      <CartesianGrid vertical={false} strokeDasharray="3 3" />
                      <XAxis
                        dataKey="name"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: string) => (v && v.length > 12 ? `${v.slice(0, 11)}…` : v)}
                      />
                      <YAxis tickLine={false} axisLine={false} />
                      <ChartTooltip
                        content={<ChartTooltipContent />}
                        formatter={(val: number) => val.toFixed(1)}
                        labelFormatter={(label: string, payload) =>
                          (payload?.[0]?.payload?.fullName as string) || label
                        }
                      />
                      <Bar
                        dataKey="frp"
                        fill="var(--color-frp)"
                        radius={[4, 4, 0, 0]}
                        label={{ position: 'top', formatter: (v: number) => v.toFixed(0), fontSize: 11 }}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartContainer>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mb-6 space-y-4">
          <div className="hidden md:block">
                  <FireFilters
                    filters={filters}
                    onFiltersChange={updateFilters}
                    onExportCSV={handleExportCSV}
                    isExporting={exportMutation.isPending}
                    defaultStatusScope="historical"
                  />
          </div>
          <div className="flex flex-wrap items-center gap-2 md:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Filter className="h-4 w-4" />
                  Filtros
                </Button>
              </SheetTrigger>
              <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto">
                <SheetHeader>
                  <SheetTitle>Filtros de incendios</SheetTitle>
                </SheetHeader>
                <div className="px-4 pb-6">
                  <FireFilters
                    filters={filters}
                    onFiltersChange={updateFilters}
                    onExportCSV={handleExportCSV}
                    isExporting={exportMutation.isPending}
                    defaultStatusScope="historical"
                    showExportButton={false}
                  />
                </div>
              </SheetContent>
            </Sheet>
            <Button
              variant="outline"
              onClick={handleExportCSV}
              disabled={exportMutation.isPending}
              className="gap-2"
            >
              {exportMutation.isPending ? 'Exportando...' : 'Exportar CSV'}
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Switch
                id="show-coordinates"
                checked={showCoordinates}
                onCheckedChange={setShowCoordinates}
              />
              <label htmlFor="show-coordinates">Mostrar coordenadas</label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="show-advanced"
                checked={showAdvancedColumns}
                onCheckedChange={setShowAdvancedColumns}
              />
              <label htmlFor="show-advanced">Columnas avanzadas</label>
            </div>
            <div className="flex items-center gap-2">
              <Table2 className="h-4 w-4" />
              <span>Vista de tabla optimizada</span>
            </div>
          </div>
        </div>

        {listErrorMessage && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4" />
            {listErrorMessage}
          </div>
        )}

        <div className="space-y-4">
          <div className="md:hidden space-y-3">
            {!isFetching && fires.length === 0 && (
              <Card>
                <CardContent className="py-6 text-center">
                  No se encontraron incendios con los filtros actuales.
                </CardContent>
              </Card>
            )}
            {fires.map((fire) => {
              const statusKey = fire.status || 'extinguished'
              const statusText = statusLabel[statusKey] || statusKey
              const statusClass = statusBadgeClasses[statusKey] || statusBadgeClasses.extinguished
              const countAreas = fire.count_protected_areas ?? 0

              return (
                <Card key={fire.id} onMouseEnter={() => prefetchFire(fire.id)}>
                  <CardContent className="space-y-3 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs text-muted-foreground">Provincia</p>
                        <p className="text-sm font-semibold">{fire.province || '—'}</p>
                        <p className="text-xs text-muted-foreground">{fire.department || '—'}</p>
                      </div>
                      <Badge variant="outline" className={cn('border', statusClass)}>
                        {statusText}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                      <div>
                        <span className="block">Inicio</span>
                        <span className="text-foreground">{formatDate(fire.start_date)}</span>
                      </div>
                      <div>
                        <span className="block">Area</span>
                        <span className="text-foreground">
                          {formatHectares(fire.estimated_area_hectares)}
                        </span>
                      </div>
                      <div>
                        <span className="block">FRP max</span>
                        <span className="text-foreground">
                          {fire.max_frp !== null && fire.max_frp !== undefined
                            ? fire.max_frp.toFixed(1)
                            : '—'}
                        </span>
                      </div>
                      <div>
                        <span className="block">Detecciones</span>
                        <span className="text-foreground">{formatNumber(fire.total_detections)}</span>
                      </div>
                      <div>
                        <span className="block">Area protegida</span>
                        <span className="text-foreground">
                          {fire.in_protected_area ? 'Si' : 'No'}
                        </span>
                      </div>
                      <div>
                        <span className="block">% afectado</span>
                        <span className="text-foreground">{formatPercent(fire.overlap_percentage)}</span>
                      </div>
                      <div>
                        <span className="block">Areas</span>
                        <span className="text-foreground">{countAreas || '—'}</span>
                      </div>
                      <div>
                        <span className="block">Significativo</span>
                        <span className="text-foreground">{fire.is_significant ? 'Si' : 'No'}</span>
                      </div>
                    </div>
                    {fire.protected_area_name && (
                      <div className="text-xs text-muted-foreground">
                        <span className="block">Nombre area protegida</span>
                        <span className="text-foreground">{fire.protected_area_name}</span>
                      </div>
                    )}
                    {showCoordinates && fire.centroid && (
                      <div className="text-xs text-muted-foreground">
                        <span className="block">Coordenadas</span>
                        <span className="text-foreground">
                          {fire.centroid.latitude.toFixed(3)}, {fire.centroid.longitude.toFixed(3)}
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })}
            {isFetching && fires.length > 0 && (
              <div className="flex items-center justify-center gap-2 py-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Cargando página siguiente…</span>
              </div>
            )}
          </div>

          <div className="hidden rounded-xl border border-border bg-background md:block">
            <div
              ref={tableContainerRef}
              className="overflow-auto max-h-[70vh]"
              onScroll={handleTableScroll}
            >
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-background/95 backdrop-blur">
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Inicio</TableHead>
                    {showAdvancedColumns && <TableHead className="hidden lg:table-cell">Fin</TableHead>}
                    {showAdvancedColumns && <TableHead className="hidden lg:table-cell">Duración</TableHead>}
                    <TableHead>Provincia</TableHead>
                    {showAdvancedColumns && <TableHead className="hidden lg:table-cell">Departamento</TableHead>}
                    <TableHead>Estado</TableHead>
                    <TableHead>Area (ha)</TableHead>
                    {showAdvancedColumns && <TableHead className="hidden xl:table-cell">Detecciones</TableHead>}
                    {showAdvancedColumns && <TableHead className="hidden xl:table-cell">FRP max</TableHead>}
                    {showAdvancedColumns && <TableHead className="hidden xl:table-cell">Confianza</TableHead>}
                    {showAdvancedColumns && <TableHead className="hidden lg:table-cell">Significativo</TableHead>}
                    <TableHead className="hidden lg:table-cell">En area protegida</TableHead>
                    {showAdvancedColumns && <TableHead className="hidden xl:table-cell">Area protegida</TableHead>}
                    <TableHead>% afectado</TableHead>
                    <TableHead>Areas</TableHead>
                    {showAdvancedColumns && <TableHead className="hidden lg:table-cell">Imagenes</TableHead>}
                    {showCoordinates && <TableHead className="hidden xl:table-cell">Coordenadas</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isFetching && totalRows === 0 && (
                    <>
                      {skeletonRows.map((_, rowIdx) => (
                        <TableRow key={`skeleton-${rowIdx}`} className="animate-pulse">
                          {Array.from({ length: tableColumnCount }).map((__, cellIdx) => (
                            <TableCell key={`skeleton-cell-${rowIdx}-${cellIdx}`}>
                              <div className="h-3 w-full rounded bg-slate-200" />
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </>
                  )}
                  {!isFetching && totalRows === 0 && (
                    <TableRow>
                      <TableCell colSpan={tableColumnCount} className="py-10 text-center">
                        No se encontraron incendios con los filtros actuales.
                      </TableCell>
                    </TableRow>
                  )}
                  {paddingTop > 0 && (
                    <TableRow>
                      <TableCell colSpan={tableColumnCount} style={{ height: paddingTop }} />
                    </TableRow>
                  )}
                  {visibleRows.map((row) => (
                    <FireRow
                      key={row.id}
                      row={row}
                      showAdvancedColumns={showAdvancedColumns}
                      showCoordinates={showCoordinates}
                      onHover={prefetchFire}
                    />
                  ))}
                  {paddingBottom > 0 && (
                    <TableRow>
                      <TableCell colSpan={tableColumnCount} style={{ height: paddingBottom }} />
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>

        {pagination && (
          <div className="mt-6">
            <Pagination
              pagination={pagination}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
              pageSizeOptions={isMobile ? [20, 30, 50] : [20, 30, 50, 100]}
            />
          </div>
        )}
      </div>
    </div>
  )
}
