import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Calendar,
  CheckCircle2,
  Compass,
  FileText,
  Loader2,
  MapPin,
  Minus,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useCreditBalance } from '@/hooks/queries/useCreditBalance'
import { cn } from '@/lib/utils'
import { groupEventsByEpisode } from '@/services/clustering'
import {
  searchFireEvents,
  getExplorationPreview,
} from '@/services/endpoints/fire-events'
import { geocodeLocation, reverseGeocode } from '@/services/endpoints/geocode'
import { getFireProvinces } from '@/services/endpoints/fires'
import {
  addExplorationItem,
  createExploration,
  deleteExplorationItem,
  generateExploration,
  getExplorationQuote,
  updateExploration,
} from '@/services/endpoints/explorations'
import type { FireSearchItem, ExplorationPreviewResponse } from '@/types/fire'
import type { ExplorationQuoteResponse } from '@/types/exploration'
import { getFireTitle } from '@/types/fire'
import type { FireMapItem } from '@/types/map'

const FireMap = lazy(() => import('@/components/fire-map').then((mod) => ({ default: mod.FireMap })))

function normalizeForProvince(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .trim()
}

type StepId = 1 | 2 | 3

type DraftItem = {
  id: string
  kind: 'pre' | 'post'
  targetDate: string
}

const PROVINCES = [
  'Buenos Aires',
  'Catamarca',
  'Chaco',
  'Chubut',
  'C\u00f3rdoba',
  'Corrientes',
  'Entre R\u00edos',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuqu\u00e9n',
  'R\u00edo Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucum\u00e1n',
]

const BEFORE_LIMIT = 3
const AFTER_LIMIT = 9
const TOTAL_LIMIT = 12
const BEFORE_OFFSETS = [-12, -6, -3]
const AFTER_OFFSETS = [3, 6, 12, 18, 24, 30, 36, 42, 48]

function createDraftId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function parseIsoDate(value?: string | null): Date | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))
}

function toDateOnly(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function addMonths(base: Date, months: number): Date {
  const year = base.getUTCFullYear()
  const month = base.getUTCMonth()
  const day = base.getUTCDate()
  const nextMonth = month + months
  const nextYear = year + Math.floor(nextMonth / 12)
  const normalizedMonth = ((nextMonth % 12) + 12) % 12
  const lastDay = new Date(Date.UTC(nextYear, normalizedMonth + 1, 0)).getUTCDate()
  const safeDay = Math.min(day, lastDay)
  return new Date(Date.UTC(nextYear, normalizedMonth, safeDay))
}

function buildDateList(
  base: string[] | undefined,
  baseDate: Date | null,
  offsets: number[],
  count: number,
  maxDate?: string,
) {
  const result: string[] = []
  const seen = new Set<string>()
  const baseValues = base ?? []
  const isAllowed = (value: string) => (maxDate ? value <= maxDate : true)

  for (const value of baseValues) {
    if (result.length >= count) break
    if (!seen.has(value) && isAllowed(value)) {
      result.push(value)
      seen.add(value)
    }
  }

  if (!baseDate) return result.slice(0, count)

  for (const offset of offsets) {
    if (result.length >= count) break
    const next = toDateOnly(addMonths(baseDate, offset))
    if (!seen.has(next) && isAllowed(next)) {
      result.push(next)
      seen.add(next)
    }
  }

  return result.slice(0, count)
}

function buildDraftItems(
  preview: ExplorationPreviewResponse,
  beforeCount: number,
  afterCount: number,
  maxDate?: string,
): DraftItem[] {
  const startDate = parseIsoDate(preview.start_date)
  const endDate = parseIsoDate(preview.end_date) ?? startDate

  const beforeDates = buildDateList(
    preview.timeline?.before ?? [],
    startDate,
    BEFORE_OFFSETS,
    beforeCount,
    maxDate,
  )
  const afterDates = buildDateList(
    preview.timeline?.after ?? [],
    endDate,
    AFTER_OFFSETS,
    afterCount,
    maxDate,
  )

  const items: DraftItem[] = []

  beforeDates.forEach((date) => {
    items.push({ id: createDraftId(), kind: 'pre', targetDate: date })
  })
  afterDates.forEach((date) => {
    items.push({ id: createDraftId(), kind: 'post', targetDate: date })
  })

  return items
}

function buildRadiusBbox(lat: number, lon: number, radiusMeters: number): string {
  const latDelta = radiusMeters / 111000
  const cosLat = Math.cos((lat * Math.PI) / 180)
  const safeCos = Math.max(Math.abs(cosLat), 0.000001)
  const lngDelta = radiusMeters / (111000 * safeCos)

  const west = lon - lngDelta
  const south = lat - latDelta
  const east = lon + lngDelta
  const north = lat + latDelta

  return [west, south, east, north].join(',')
}

function normalizeCounts(before: number, after: number) {
  let safeBefore = Math.max(0, Math.min(BEFORE_LIMIT, before))
  let safeAfter = Math.max(0, Math.min(AFTER_LIMIT, after))
  let total = safeBefore + safeAfter

  if (total === 0) {
    safeAfter = 1
    total = 1
  }

  if (total > TOTAL_LIMIT) {
    safeAfter = Math.min(safeAfter, TOTAL_LIMIT - safeBefore)
    total = safeBefore + safeAfter
  }

  return { before: safeBefore, after: safeAfter }
}

function formatDisplayDate(value: string, locale: string) {
  const parsed = parseIsoDate(value)
  if (!parsed) return value
  return new Intl.DateTimeFormat(locale).format(parsed)
}

function getStatusLabel(status: FireSearchItem['status'] | undefined, t: (key: string) => string) {
  if (!status) return t('monitoring')
  if (status === 'active') return t('active')
  if (status === 'controlled') return t('monitoring')
  if (status === 'extinguished') return t('extinguished')
  return t('monitoring')
}

function mapQualityToSeverity(score?: number | null): FireMapItem['severity'] {
  if (!score) return 'low'
  if (score >= 70) return 'high'
  if (score >= 45) return 'medium'
  return 'low'
}

export default function ExplorationPage() {
  const { t, language } = useI18n()
  const { isAuthenticated, status } = useAuth()
  const locale = language === 'es' ? 'es-AR' : 'en-US'
  const navigate = useNavigate()
  const today = new Date().toISOString().slice(0, 10)

  const mapFallback = (
    <div className="flex h-64 items-center justify-center rounded-lg border border-border bg-muted/40">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>{t('explorationMapLoading')}</span>
      </div>
    </div>
  )

  const [step, setStep] = useState<StepId>(1)
  const [provinceOptions, setProvinceOptions] = useState<string[]>(PROVINCES)
  const [searchProvince, setSearchProvince] = useState<string>('')
  const [searchFrom, setSearchFrom] = useState<string>('')
  const [searchTo, setSearchTo] = useState<string>('')
  const [searchText, setSearchText] = useState<string>('')
  const [searchResults, setSearchResults] = useState<FireSearchItem[]>([])
  const [searchPage, setSearchPage] = useState(1)
  const [searchHasNext, setSearchHasNext] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [addressNotInProvinceError, setAddressNotInProvinceError] = useState<string | null>(null)
  const [datesRequiredError, setDatesRequiredError] = useState<string | null>(null)
  const [coordLat, setCoordLat] = useState('')
  const [coordLon, setCoordLon] = useState('')
  const [coordRadius, setCoordRadius] = useState('5000')
  const [coordError, setCoordError] = useState<string | null>(null)

  const [showMap, setShowMap] = useState(false)
  const [advancedId, setAdvancedId] = useState('')

  const [selectedFire, setSelectedFire] = useState<FireSearchItem | null>(null)
  const [preview, setPreview] = useState<ExplorationPreviewResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const [beforeCount, setBeforeCount] = useState(1)
  const [afterCount, setAfterCount] = useState(3)
  const [draftItems, setDraftItems] = useState<DraftItem[]>([])

  const [draftTitle, setDraftTitle] = useState('')
  const [draftId, setDraftId] = useState<string | null>(null)
  const [draftItemIds, setDraftItemIds] = useState<string[]>([])
  const [quote, setQuote] = useState<ExplorationQuoteResponse | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncedSignature, setSyncedSignature] = useState('')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [showCreditDialog, setShowCreditDialog] = useState(false)
  const [showAuthDialog, setShowAuthDialog] = useState(false)
  const [pauseAutoSync, setPauseAutoSync] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [trackingId, setTrackingId] = useState<string | null>(null)
  const [titleError, setTitleError] = useState(false)

  const [newItemKind, setNewItemKind] = useState<'pre' | 'post'>('post')
  const [newItemDate, setNewItemDate] = useState('')
  const itemsSignature = useMemo(
    () => draftItems.map((item) => `${item.kind}-${item.targetDate}`).join('|'),
    [draftItems],
  )

  const needsSync = step === 3 && itemsSignature !== syncedSignature

  const totalCount = beforeCount + afterCount

  const groupedResults = useMemo(() => groupEventsByEpisode(searchResults), [searchResults])
  const { data: creditData } = useCreditBalance()

  const mapItems = useMemo(() => {
    return groupedResults
      .map((group) => {
        const fire = group.representative
        const centroid = group.centroid ?? fire.centroid
        const lat = centroid?.latitude
        const lon = centroid?.longitude
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
        return {
          id: fire.id,
          title: getFireTitle(fire.department, fire.province),
          lat: lat ?? 0,
          lon: lon ?? 0,
          severity: mapQualityToSeverity(fire.quality_score),
          province: fire.province,
          status: fire.status,
          date: fire.start_date,
          hectares: fire.estimated_area_hectares ?? null,
        } as FireMapItem
      })
      .filter(Boolean) as FireMapItem[]
  }, [groupedResults])

  const selectedMapItem = useMemo(() => {
    if (!selectedFire?.centroid) return null
    return {
      id: selectedFire.id,
      title: getFireTitle(selectedFire.department, selectedFire.province),
      lat: selectedFire.centroid.latitude,
      lon: selectedFire.centroid.longitude,
      severity: mapQualityToSeverity(selectedFire.quality_score),
      province: selectedFire.province,
      status: selectedFire.status,
      date: selectedFire.start_date,
      hectares: selectedFire.estimated_area_hectares ?? null,
    } as FireMapItem
  }, [selectedFire])

  useEffect(() => {
    let mounted = true
    const loadProvinces = async () => {
      try {
        const response = await getFireProvinces()
        const names = response.provinces
          .map((province) => province.name)
          .filter((name): name is string => Boolean(name))
        if (mounted && names.length) {
          setProvinceOptions(names)
        }
      } catch {
        // keep fallback list
      }
    }
    void loadProvinces()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (step !== 2 || !preview) return
    setDraftItems(buildDraftItems(preview, beforeCount, afterCount, today))
  }, [step, preview, beforeCount, afterCount, today])

  useEffect(() => {
    if (step !== 3 || !preview || !selectedFire) return
    if (!needsSync || syncing || draftItems.length === 0 || showAuthDialog || pauseAutoSync) return
    void syncDraftAndQuote()
  }, [
    step,
    preview,
    selectedFire,
    needsSync,
    syncing,
    draftItems,
    showAuthDialog,
    pauseAutoSync,
    status,
    isAuthenticated,
  ])

  const resetDraftState = () => {
    setDraftId(null)
    setDraftItemIds([])
    setQuote(null)
    setSyncedSignature('')
    setTrackingId(null)
    setPauseAutoSync(false)
  }

  const handleSearch = async (page: number = 1, append: boolean = false) => {
    setSearchLoading(true)
    setSearchError(null)
    setAddressNotInProvinceError(null)
    setDatesRequiredError(null)
    setCoordError(null)
    try {
      const trimmedText = searchText?.trim() ?? ''
      const trimmedProvince = searchProvince?.trim() ?? ''
      const hasFrom = Boolean(searchFrom?.trim())
      const hasTo = Boolean(searchTo?.trim())

      if (trimmedProvince && !hasFrom && !hasTo) {
        setDatesRequiredError(t('explorationDatesRequired'))
        if (!append) setSearchResults([])
        setSearchPage(page)
        setSearchHasNext(false)
        setSearchLoading(false)
        return
      }

      const hasCoordInput =
        coordLat.trim().length > 0 ||
        coordLon.trim().length > 0
      let bbox: string | undefined

      if (hasCoordInput) {
        const latValue = coordLat.trim()
        const lonValue = coordLon.trim()
        const lat = Number(latValue)
        const lon = Number(lonValue)
        const radiusValue = coordRadius.trim().length > 0 ? Number(coordRadius) : 5000
        const isValid =
          latValue.length > 0 &&
          lonValue.length > 0 &&
          Number.isFinite(lat) &&
          Number.isFinite(lon) &&
          Number.isFinite(radiusValue) &&
          lat >= -90 &&
          lat <= 90 &&
          lon >= -180 &&
          lon <= 180 &&
          radiusValue >= 100 &&
          radiusValue <= 10000

        if (!isValid) {
          setCoordError(t('explorationCoordsError'))
          setSearchLoading(false)
          return
        }

        bbox = buildRadiusBbox(lat, lon, radiusValue)
      }

      const needsAddressValidation = trimmedText.length >= 2 && trimmedProvince.length > 0

      if (needsAddressValidation) {
        let geocodeResult: Awaited<ReturnType<typeof geocodeLocation>> | null = null
        try {
          geocodeResult = await geocodeLocation(trimmedText)
        } catch {
          // geocode failed
        }
        if (!geocodeResult?.result) {
          setAddressNotInProvinceError(t('explorationAddressNotInProvince'))
          if (!append) setSearchResults([])
          setSearchPage(page)
          setSearchHasNext(false)
          setSearchLoading(false)
          return
        }
        let reverseResult: Awaited<ReturnType<typeof reverseGeocode>> | null = null
        try {
          reverseResult = await reverseGeocode(geocodeResult.result.lat, geocodeResult.result.lon)
        } catch {
          // reverse geocode failed
        }
        const displayName = reverseResult?.display_name ?? ''
        const normalizedDisplay = normalizeForProvince(displayName)
        const normalizedSelected = normalizeForProvince(trimmedProvince)
        if (!normalizedDisplay.includes(normalizedSelected)) {
          setAddressNotInProvinceError(t('explorationAddressNotInProvince'))
          if (!append) setSearchResults([])
          setSearchPage(page)
          setSearchHasNext(false)
          setSearchLoading(false)
          return
        }
      }

      const params: Parameters<typeof searchFireEvents>[0] = { page }
      if (trimmedProvince) params.province = trimmedProvince
      if (searchFrom?.trim()) params.date_from = searchFrom.trim()
      if (searchTo?.trim()) params.date_to = searchTo.trim()
      if (trimmedText) params.q = trimmedText
      if (bbox) params.bbox = bbox

      const response = await searchFireEvents(params)

      setSearchResults((prev) => (append ? [...prev, ...response.fires] : response.fires))
      setSearchPage(page)
      setSearchHasNext(response.pagination?.has_next ?? false)
    } catch (error) {
      setSearchError(t('technicalError'))
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSelectFire = async (fire: FireSearchItem) => {
    setSelectedFire(fire)
    setPreview(null)
    resetDraftState()
    setBeforeCount(1)
    setAfterCount(3)
    setDraftItems([])
    setPreviewLoading(true)
    try {
      const data = await getExplorationPreview(fire.id)
      setPreview(data)
    } catch {
      toast.error(t('technicalError'))
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleLoadById = async () => {
    if (!advancedId.trim()) return
    setPreviewLoading(true)
    setSearchError(null)
    resetDraftState()
    try {
      const data = await getExplorationPreview(advancedId.trim())
      setPreview(data)
      setSelectedFire({
        id: data.fire_event_id,
        start_date: data.start_date,
        end_date: data.end_date,
        province: data.province,
        department: data.department,
        estimated_area_hectares: data.estimated_area_hectares,
        avg_confidence: null,
        quality_score: null,
        total_detections: 0,
        has_satellite_imagery: data.has_satellite_imagery,
        centroid: data.centroid ?? undefined,
        status: undefined,
      })
    } catch (error) {
      toast.error(t('technicalError'))
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleMapSelect = (item: FireMapItem) => {
    const group = groupedResults.find((result) => result.representative.id === item.id)
    if (group) {
      void handleSelectFire(group.representative)
    }
  }

  const handleBeforeChange = (value: number) => {
    const normalized = normalizeCounts(value, afterCount)
    setBeforeCount(normalized.before)
    setAfterCount(normalized.after)
  }

  const handleAfterChange = (value: number) => {
    const normalized = normalizeCounts(beforeCount, value)
    setBeforeCount(normalized.before)
    setAfterCount(normalized.after)
  }

  const handleTotalChange = (value: number) => {
    const desired = Math.max(1, Math.min(TOTAL_LIMIT, value))
    let nextBefore = beforeCount
    let nextAfter = desired - nextBefore
    if (nextAfter > AFTER_LIMIT) {
      nextAfter = AFTER_LIMIT
      nextBefore = desired - nextAfter
    }
    if (nextBefore > BEFORE_LIMIT) {
      nextBefore = BEFORE_LIMIT
      nextAfter = desired - nextBefore
    }
    const normalized = normalizeCounts(nextBefore, nextAfter)
    setBeforeCount(normalized.before)
    setAfterCount(normalized.after)
  }

  const handlePreset = (before: number, after: number) => {
    const normalized = normalizeCounts(before, after)
    setBeforeCount(normalized.before)
    setAfterCount(normalized.after)
  }

  const handleMoveItem = (index: number, direction: number) => {
    setDraftItems((items) => {
      const next = [...items]
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= next.length) return items
      const temp = next[index]
      next[index] = next[targetIndex]
      next[targetIndex] = temp
      return next
    })
  }

  const handleRemoveItem = (id: string) => {
    setDraftItems((items) => items.filter((item) => item.id !== id))
  }

  const handleAddItem = () => {
    if (!newItemDate) return
    if (newItemDate > today) {
      toast.error('La fecha no puede ser futura.')
      return
    }
    if (draftItems.length >= TOTAL_LIMIT) {
      toast.error(t('reportMaxImagesRange'))
      return
    }
    setDraftItems((items) => [
      ...items,
      { id: createDraftId(), kind: newItemKind, targetDate: newItemDate },
    ])
    setNewItemDate('')
  }

  const syncDraftAndQuote = async () => {
    if (!selectedFire || !preview) return
    if (draftItems.length === 0) return
    if (status === 'loading') return
    if (!isAuthenticated) {
      setPauseAutoSync(true)
      setShowAuthDialog(true)
      return
    }
    setSyncing(true)
    try {
      let currentId = draftId
      if (!currentId) {
        const created = await createExploration({
          fire_event_id: selectedFire.id,
          title: draftTitle || undefined,
        })
        currentId = created.id
        setDraftId(created.id)
      } else if (draftTitle) {
        await updateExploration(currentId, { title: draftTitle })
      }

      if (draftItemIds.length > 0) {
        await Promise.allSettled(
          draftItemIds.map((itemId) => deleteExplorationItem(currentId!, itemId)),
        )
      }

      const createdIds: string[] = []
      for (const item of draftItems) {
        const response = await addExplorationItem(currentId!, {
          kind: item.kind,
          target_date: new Date(`${item.targetDate}T00:00:00Z`).toISOString(),
        })
        createdIds.push(response.id)
      }
      setDraftItemIds(createdIds)

      const quoteResponse = await getExplorationQuote(currentId!)
      setQuote(quoteResponse)
      setSyncedSignature(itemsSignature)
      setPauseAutoSync(false)
    } catch (error) {
      if ((error as { response?: { status?: number } })?.response?.status === 401) {
        setPauseAutoSync(true)
        setShowAuthDialog(true)
        return
      }
      toast.error(t('technicalError'))
    } finally {
      setSyncing(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!draftId) return
    if (!draftTitle.trim()) {
      setTitleError(true)
      return
    }
    setTitleError(false)
    try {
      if (draftTitle) {
        await updateExploration(draftId, { title: draftTitle })
      }
      toast.success(t('explorationSaved'))
    } catch (error) {
      toast.error(t('technicalError'))
    }
  }

  const handleContinueToStep3 = () => {
    if (!canContinueToStep3 || status === 'loading') return
    if (isAuthenticated) {
      setShowAuthDialog(false)
      setPauseAutoSync(false)
      setStep(3)
      return
    }
    setShowAuthDialog(true)
  }

  const handleAuthBack = () => {
    setShowAuthDialog(false)
    setStep(2)
  }

  const handleAuthRedirect = () => {
    setShowAuthDialog(false)
    navigate('/login')
  }

  const handleGenerate = () => {
    if (!isAuthenticated) {
      setShowAuthDialog(true)
      return
    }
    if (creditData && creditData.balance < draftItems.length) {
      setShowCreditDialog(true)
      return
    }
    setShowConfirmDialog(true)
  }

  const confirmGenerate = async () => {
    if (status === 'loading') return
    if (!isAuthenticated) {
      setShowAuthDialog(true)
      return
    }
    if (!draftId) {
      toast.error(t('technicalError'))
      return
    }
    setGenerating(true)
    try {
      const idempotencyKey = crypto.randomUUID()
      const response = await generateExploration(draftId, idempotencyKey)
      setTrackingId(response.job_id)
      toast.success(`${t('explorationGenerationStarted')} ${response.job_id}`)
    } catch (error) {
      const response = (error as { response?: { status?: number; data?: any; headers?: any } })
        ?.response
      const requestId = response?.headers?.['x-request-id']
      if (response?.data) {
        // eslint-disable-next-line no-console
        console.error('Exploration generation failed', response.data, requestId)
      }
      const detail = response?.data?.detail
      let message = t('technicalError')
      if (typeof detail === 'string') {
        message = detail
      } else if (detail?.message) {
        message = detail.message
      }
      if (requestId) {
        message = `${message} (ID: ${requestId})`
      }
      toast.error(message)
    } finally {
      setGenerating(false)
      setShowConfirmDialog(false)
    }
  }

  const costUnit = quote?.unit_price_ars ?? 500
  const fallbackTotal = costUnit * draftItems.length
  const costTotal = quote && !needsSync ? quote.total_price_ars : fallbackTotal
  const showEstimated = !quote || needsSync
  const costFormatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'ARS',
    maximumFractionDigits: 0,
  })

  const canContinueToStep2 = Boolean(selectedFire && preview && !previewLoading)
  const canContinueToStep3 = Boolean(draftItems.length > 0 && totalCount <= TOTAL_LIMIT)

  return (
    <div className="bg-background">
      <AlertDialog open={showAuthDialog} onOpenChange={setShowAuthDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('explorationAuthTitle')}</AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>{t('explorationAuthMessageLine1')}</p>
              <p>{t('explorationAuthMessageLine2')}</p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleAuthBack}>{t('explorationAuthBack')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleAuthRedirect}>
              {t('explorationAuthLogin')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={showCreditDialog} onOpenChange={setShowCreditDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Necesitas cargar creditos</AlertDialogTitle>
            <AlertDialogDescription>
              No tenes saldo suficiente para generar estas imagenes HD.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Volver</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowCreditDialog(false)
                navigate('/credits')
              }}
            >
              Ir a MercadoPago
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog
        open={showConfirmDialog}
        onOpenChange={(open) => {
          if (!generating) setShowConfirmDialog(open)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('explorationConfirmTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('explorationConfirmDescription')} {costFormatter.format(costTotal)}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={generating}>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmGenerate} disabled={generating}>
              {generating ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('loading')}
                </span>
              ) : (
                t('explorationConfirmAction')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <div className="container mx-auto space-y-8 px-4 py-6">
        <Card className="border-border/60 bg-card/60">
          <CardContent className="grid gap-6 py-6 lg:grid-cols-[1.2fr_1fr]">
            <div className="space-y-4">
              <div>
                <h1 className="text-3xl font-bold text-foreground mb-[20px]">{t('reportsTitle')}</h1>
                <p className="text-sm text-muted-foreground">{t('explorationInstruction')}</p>
                <div className="mt-4 space-y-2">
                  <h2 className="text-sm font-semibold text-foreground">{t('explorationHowTitle')}</h2>
                  <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                    <li>{t('explorationHowStep1')}</li>
                    <li>{t('explorationHowStep2')}</li>
                    <li>{t('explorationHowStep3')}</li>
                  </ul>
                </div>
              </div>
            </div>

            <Card className="border-dashed">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">{t('explorationDemoTitle')}</CardTitle>
                <CardDescription>{t('explorationDemoHint')}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2">
                {[t('explorationBeforeLabel'), t('explorationAfterLabel')].map((label) => (
                  <div
                    key={label}
                    className="flex flex-col gap-2 rounded-lg border border-border bg-muted/30 p-3"
                  >
                    <Badge variant="secondary" className="w-fit">
                      {label}
                    </Badge>
                    <div className="aspect-video rounded-md bg-gradient-to-br from-emerald-100 via-amber-50 to-orange-200 opacity-80" />
                    <p className="text-xs text-muted-foreground">{t('explorationDemoExample')}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-1">
                <CardTitle>{t(`explorationStep${step}Title`)}</CardTitle>
                <CardDescription>{t(`explorationStep${step}Subtitle`)}</CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground" data-testid="exploration-stepper">
                {[1, 2, 3].map((id) => (
                  <div key={id} className="flex items-center gap-2">
                    <span
                      className={cn(
                        'flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold',
                        step === id ? 'border-primary bg-primary text-primary-foreground' : 'border-border',
                      )}
                    >
                      {id}
                    </span>
                    <span className={step === id ? 'text-foreground' : ''}>
                      {t(`explorationStep${id}Title`)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {step === 1 && (
              <div className="space-y-6">
                <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
                  <Card className="border-border/70 min-w-0">
                    <CardHeader>
                      <CardTitle className="text-base">{t('explorationStep1Title')}</CardTitle>
                      <CardDescription>{t('explorationStep1Subtitle')}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground">{t('province')}</span>
                          <Select
                            value={searchProvince || 'all'}
                            onValueChange={(value) => {
                              setSearchProvince(value === 'all' ? '' : value)
                              setAddressNotInProvinceError(null)
                              setDatesRequiredError(null)
                            }}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder={t('filter')} />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="all">{t('all')}</SelectItem>
                              {provinceOptions.map((province) => (
                                <SelectItem key={province} value={province}>
                                  {province}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <span className="text-xs font-semibold text-muted-foreground">{t('date')}</span>
                          <div className="grid grid-cols-2 gap-2">
                            <Input
                              type="date"
                              value={searchFrom}
                              onChange={(event) => {
                                setSearchFrom(event.target.value)
                                setDatesRequiredError(null)
                              }}
                              max={today}
                            />
                            <Input
                              type="date"
                              value={searchTo}
                              onChange={(event) => {
                                setSearchTo(event.target.value)
                                setDatesRequiredError(null)
                              }}
                              max={today}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">{t('search')}</span>
                        <Input
                          value={searchText}
                          onChange={(event) => {
                            setSearchText(event.target.value)
                            setAddressNotInProvinceError(null)
                          }}
                          placeholder={t('explorationSearchPlaceholder')}
                        />
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          onClick={() => handleSearch(1, false)}
                          disabled={searchLoading}
                          className="gap-2"
                          data-testid="exploration-btn-search"
                        >
                          {searchLoading ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              {t('loading')}
                            </>
                          ) : (
                            <>
                              <Search className="h-4 w-4" />
                              {t('search')}
                            </>
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setShowMap((prev) => !prev)}
                          className="gap-2"
                          data-testid="exploration-btn-map"
                        >
                          <MapPin className="h-4 w-4" />
                          {t('explorationMapSelect')}
                        </Button>
                      </div>

                      <Accordion type="single" collapsible>
                        <AccordionItem value="coords">
                          <AccordionTrigger className="text-sm font-semibold">
                            {t('explorationCoordsTitle')}
                          </AccordionTrigger>
                          <AccordionContent className="space-y-3 pt-2">
                            <p className="text-xs text-muted-foreground">
                              {t('explorationCoordsHint')}
                            </p>
                            <div className="grid gap-3 sm:grid-cols-3">
                              <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground">
                                  {t('latitude')}
                                </span>
                                <Input
                                  type="number"
                                  step="0.0001"
                                  inputMode="decimal"
                                  value={coordLat}
                                  onChange={(event) => {
                                    setCoordLat(event.target.value)
                                    setCoordError(null)
                                  }}
                                  placeholder="-34.6037"
                                />
                              </div>
                              <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground">
                                  {t('longitude')}
                                </span>
                                <Input
                                  type="number"
                                  step="0.0001"
                                  inputMode="decimal"
                                  value={coordLon}
                                  onChange={(event) => {
                                    setCoordLon(event.target.value)
                                    setCoordError(null)
                                  }}
                                  placeholder="-58.3816"
                                />
                              </div>
                              <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground">
                                  {t('radiusMeters')}
                                </span>
                                <Input
                                  type="number"
                                  min={100}
                                  max={10000}
                                  inputMode="numeric"
                                  value={coordRadius}
                                  onChange={(event) => {
                                    setCoordRadius(event.target.value)
                                    setCoordError(null)
                                  }}
                                  placeholder="5000"
                                />
                              </div>
                            </div>
                            {coordError && (
                              <p className="text-xs text-destructive">{coordError}</p>
                            )}
                          </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="advanced">
                          <AccordionTrigger className="text-sm font-semibold">
                            {t('explorationAdvancedIdLabel')}
                          </AccordionTrigger>
                          <AccordionContent className="space-y-3 pt-2">
                            <Input
                              value={advancedId}
                              onChange={(event) => setAdvancedId(event.target.value)}
                              placeholder={t('explorationAdvancedIdPlaceholder')}
                            />
                            <Button variant="outline" onClick={handleLoadById} className="gap-2">
                              <Compass className="h-4 w-4" />
                              {t('explorationAdvancedIdAction')}
                            </Button>
                          </AccordionContent>
                        </AccordionItem>
                      </Accordion>
                    </CardContent>
                  </Card>

                  <Card className="border-border/70 min-w-0" data-testid="exploration-results">
                    <CardHeader>
                      <CardTitle className="text-base">{t('explorationResults')}</CardTitle>
                      <CardDescription>
                        {selectedFire ? (
                          <span className="flex items-center gap-2 text-emerald-600">
                            <CheckCircle2 className="h-4 w-4" />
                            {t('explorationSelected')}
                          </span>
                        ) : (
                          t('explorationStep1Subtitle')
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {previewLoading && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t('loading')}
                        </div>
                      )}
                      {searchError && <p className="text-sm text-destructive">{searchError}</p>}
                      {addressNotInProvinceError && (
                        <p className="text-sm text-muted-foreground">{addressNotInProvinceError}</p>
                      )}
                      {datesRequiredError && (
                        <p className="text-sm text-muted-foreground">{datesRequiredError}</p>
                      )}
                      {!searchLoading && searchResults.length === 0 && !searchError && !addressNotInProvinceError && !datesRequiredError && (
                        <div className="space-y-2 text-sm text-muted-foreground">
                          <p className="font-semibold text-foreground">{t('explorationNoResultsTitle')}</p>
                          <p>{t('explorationNoResultsHint')}</p>
                        </div>
                      )}
                      {groupedResults.length > 0 && (
                        <div className="overflow-x-auto pb-2">
                          <div className="flex w-max gap-2">
                            {groupedResults.map((group) => {
                              const fire = group.representative
                              const isSelected = selectedFire?.id === fire.id
                              return (
                                <div key={fire.id} className="w-[260px] shrink-0">
                                  <Card
                                    className={cn(
                                      'border-border/70 gap-3 py-3',
                                      isSelected && 'border-primary',
                                    )}
                                  >
                                    <CardContent className="flex flex-col gap-2 p-3">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <Badge variant={isSelected ? 'default' : 'secondary'}>
                                          {getStatusLabel(fire.status, t)}
                                        </Badge>
                                        {group.events.length > 1 && (
                                          <Badge variant="outline">
                                            {group.events.length} {t('eventsLabel')}
                                          </Badge>
                                        )}
                                        {fire.has_satellite_imagery && (
                                          <Badge variant="outline">HD</Badge>
                                        )}
                                      </div>
                                      <div>
                                        <p className="text-sm font-semibold text-foreground">
                                          {getFireTitle(fire.department, fire.province)}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                          <Calendar className="mr-1 inline h-3 w-3" />
                                          {formatDisplayDate(fire.start_date, locale)} -{' '}
                                          {formatDisplayDate(fire.end_date, locale)}
                                        </p>
                                      </div>
                                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                                        <span>
                                          {t('hectares')}:{' '}
                                          {fire.estimated_area_hectares?.toFixed(1) ?? '-'}
                                        </span>
                                        <span>
                                          {t('detections')}: {fire.total_detections ?? 0}
                                        </span>
                                      </div>
                                      <Button
                                        type="button"
                                        size="sm"
                                        onClick={() => handleSelectFire(fire)}
                                        variant={isSelected ? 'default' : 'outline'}
                                        className="gap-2"
                                      >
                                        {isSelected ? (
                                          <>
                                            <CheckCircle2 className="h-4 w-4" />
                                            {t('explorationSelected')}
                                          </>
                                        ) : (
                                          <>
                                            <ArrowRight className="h-4 w-4" />
                                            {t('explorationSelect')}
                                          </>
                                        )}
                                      </Button>
                                    </CardContent>
                                  </Card>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                      {searchHasNext && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleSearch(searchPage + 1, true)}
                          disabled={searchLoading}
                        >
                          {t('explorationLoadMore')}
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {showMap && (
                  <Card className="border-border/70 isolate">
                    <CardHeader>
                      <CardTitle className="text-base">{t('map')}</CardTitle>
                      <CardDescription>{t('explorationMapSelect')}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Suspense fallback={mapFallback}>
                        <FireMap
                          fires={mapItems}
                          selectedFire={selectedMapItem}
                          onFireSelect={handleMapSelect}
                          height="h-72"
                          popupVariant="fire_detail"
                        />
                      </Suspense>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
            {step === 2 && (
              <div className="space-y-6">
                <Card className="border-border/70">
                  <CardHeader>
                    <CardTitle className="text-base">{t('explorationStep2Title')}</CardTitle>
                    <CardDescription>{t('explorationStep2Subtitle')}</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-6 lg:grid-cols-[1fr_1fr]">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">
                          {t('explorationBeforeLabel')}
                        </span>
                        <div className="flex items-center gap-3">
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => handleBeforeChange(beforeCount - 1)}
                            disabled={beforeCount <= 0}
                          >
                            <Minus className="h-4 w-4" />
                          </Button>
                          <span className="text-lg font-semibold">{beforeCount}</span>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => handleBeforeChange(beforeCount + 1)}
                            disabled={beforeCount >= BEFORE_LIMIT}
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">
                          {t('explorationAfterLabel')}
                        </span>
                        <div className="flex items-center gap-3">
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => handleAfterChange(afterCount - 1)}
                            disabled={afterCount <= 0}
                          >
                            <Minus className="h-4 w-4" />
                          </Button>
                          <span className="text-lg font-semibold">{afterCount}</span>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => handleAfterChange(afterCount + 1)}
                            disabled={afterCount >= AFTER_LIMIT}
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">
                          {t('explorationTotalLabel')}: {totalCount}
                        </span>
                        <Slider
                          value={[totalCount]}
                          min={1}
                          max={TOTAL_LIMIT}
                          step={1}
                          onValueChange={(value) => handleTotalChange(value[0] ?? totalCount)}
                        />
                      </div>

                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">
                          {t('explorationPresetsLabel')}
                        </span>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePreset(1, 3)}
                          >
                            1 + 3
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePreset(2, 6)}
                          >
                            2 + 6
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePreset(3, 9)}
                          >
                            3 + 9
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">{t('explorationMoreDetail')}</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-foreground">{t('explorationTimelineTitle')}</h3>
                      <div className="space-y-3">
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-muted-foreground">
                            {t('explorationBeforeLabel')}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {draftItems
                              .filter((item) => item.kind === 'pre')
                              .map((item) => (
                                <Badge key={item.id} variant="secondary">
                                  {formatDisplayDate(item.targetDate, locale)}
                                </Badge>
                              ))}
                          </div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-muted-foreground">
                            {t('explorationAfterLabel')}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {draftItems
                              .filter((item) => item.kind === 'post')
                              .map((item) => (
                                <Badge key={item.id} variant="outline">
                                  {formatDisplayDate(item.targetDate, locale)}
                                </Badge>
                              ))}
                          </div>
                        </div>
                      </div>
                      <Separator />
                      {selectedFire && (
                        <div className="space-y-1 text-xs text-muted-foreground">
                          <p className="text-sm font-semibold text-foreground">
                            {getFireTitle(selectedFire.department, selectedFire.province)}
                          </p>
                          <p>
                            {t('date')}: {formatDisplayDate(selectedFire.start_date, locale)} -{' '}
                            {formatDisplayDate(selectedFire.end_date, locale)}
                          </p>
                          <p>
                            {t('hectares')}: {selectedFire.estimated_area_hectares?.toFixed(1) ?? '-'}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="space-y-4 lg:col-span-2">
                      <Separator />
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-muted-foreground">
                          {t('explorationAddItemLabel')}
                        </span>
                        <div className="flex flex-wrap items-center gap-2">
                          <Select
                            value={newItemKind}
                            onValueChange={(value) => setNewItemKind(value as 'pre' | 'post')}
                          >
                            <SelectTrigger className="w-[160px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="pre">{t('explorationBeforeLabel')}</SelectItem>
                              <SelectItem value="post">{t('explorationAfterLabel')}</SelectItem>
                            </SelectContent>
                          </Select>
                          <Input
                            type="date"
                            value={newItemDate}
                            onChange={(event) => setNewItemDate(event.target.value)}
                            max={today}
                          />
                          <Button variant="outline" onClick={handleAddItem}>
                            {t('explorationAddItemAction')}
                          </Button>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {draftItems.map((item, index) => (
                          <div
                            key={item.id}
                            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3"
                          >
                            <div className="flex items-center gap-3">
                              <Badge variant={item.kind === 'pre' ? 'secondary' : 'outline'}>
                                {item.kind === 'pre' ? t('explorationBeforeLabel') : t('explorationAfterLabel')}
                              </Badge>
                              <div>
                                <p className="text-sm font-semibold text-foreground">
                                  {formatDisplayDate(item.targetDate, locale)}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {item.kind === 'pre' ? t('explorationBeforeLabel') : t('explorationAfterLabel')}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleMoveItem(index, -1)}
                                disabled={index === 0}
                              >
                                <ArrowUp className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleMoveItem(index, 1)}
                                disabled={index === draftItems.length - 1}
                              >
                                <ArrowDown className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRemoveItem(item.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            {step === 3 && (
              <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
                <Card className="border-border/70">
                  <CardHeader>
                    <CardTitle className="text-base">{t('explorationStep3Title')}</CardTitle>
                    <CardDescription>{t('explorationStep3Subtitle')}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground">
                        {t('explorationTitleLabel')}
                      </span>
                      <Input
                        value={draftTitle}
                        onChange={(event) => {
                          setDraftTitle(event.target.value)
                          if (titleError) setTitleError(false)
                        }}
                        placeholder={t('explorationTitlePlaceholder')}
                      />
                      {titleError && (
                        <p className="text-xs text-destructive">
                          Ingresá un título para guardar la investigación.
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground">
                        Resumen de fechas
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {draftItems.map((item) => (
                          <Badge
                            key={item.id}
                            variant={item.kind === 'pre' ? 'secondary' : 'outline'}
                          >
                            {formatDisplayDate(item.targetDate, locale)}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </CardContent>

                  <CardFooter className="flex flex-col gap-3">
                    <div className="w-full rounded-lg border border-border bg-muted/30 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-foreground">{t('explorationCostLabel')}</p>
                          <p className="text-xs text-muted-foreground">
                            {t('explorationCostNote')}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-foreground">
                            {draftItems.length} {t('imagery')} - {costFormatter.format(costTotal)}
                          </p>
                          {showEstimated && (
                            <Badge variant="secondary">{t('explorationEstimateTag')}</Badge>
                          )}
                        </div>
                      </div>
                      {quote?.suggestions?.length ? (
                        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
                          {quote.suggestions.map((suggestion) => (
                            <li key={suggestion}>{suggestion}</li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                    {trackingId && (
                      <div className="w-full rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                        <div className="flex items-center gap-3 text-sm text-emerald-900">
                          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                          <div className="space-y-1">
                            <p className="font-semibold">{t('explorationTrackingTitle')}</p>
                            <p className="text-xs text-emerald-800">
                              {t('explorationTrackingIdLabel')}{' '}
                              <code className="rounded bg-emerald-100 px-2 py-0.5">{trackingId}</code>
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex w-full flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        className="gap-2"
                        disabled={syncing || needsSync || generating || !draftTitle.trim()}
                        onClick={handleSaveDraft}
                      >
                        <FileText className="h-4 w-4" />
                        {t('explorationSave')}
                      </Button>
                      <Button
                        className="gap-2"
                        disabled={syncing || needsSync || generating}
                        onClick={handleGenerate}
                      >
                        <Sparkles className="h-4 w-4" />
                        {t('explorationGenerate')}
                      </Button>
                      {needsSync && (
                        <Button
                          variant="outline"
                          onClick={syncDraftAndQuote}
                          className="gap-2"
                        >
                          {syncing ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              {t('explorationLoadingQuote')}
                            </>
                          ) : (
                            <>
                              <ArrowRight className="h-4 w-4" />
                              {t('explorationUpdateCost')}
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </CardFooter>
                </Card>

                <div className="space-y-4">
                  <Card className="border-border/70 isolate">
                    <CardHeader>
                      <CardTitle className="text-base">{t('explorationEventSummary')}</CardTitle>
                      <CardDescription>{t('explorationMapPreview')}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {selectedMapItem ? (
                        <Suspense fallback={mapFallback}>
                          <FireMap
                            fires={[selectedMapItem]}
                            selectedFire={selectedMapItem}
                            height="h-48"
                            interactive={false}
                            popupVariant="fire_detail"
                          />
                        </Suspense>
                      ) : (
                        <div className="flex h-48 items-center justify-center rounded-lg border border-border bg-muted/30 text-sm text-muted-foreground">
                          {t('map')}
                        </div>
                      )}
                      {selectedFire && (
                        <div className="space-y-1 text-xs text-muted-foreground">
                          <p className="text-sm font-semibold text-foreground">
                            {getFireTitle(selectedFire.department, selectedFire.province)}
                          </p>
                          <p>
                            {t('date')}: {formatDisplayDate(selectedFire.start_date, locale)} -{' '}
                            {formatDisplayDate(selectedFire.end_date, locale)}
                          </p>
                          <p>
                            {t('hectares')}: {selectedFire.estimated_area_hectares?.toFixed(1) ?? '-'}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="border-border/70">
                    <CardHeader>
                      <CardTitle className="text-base">{t('explorationDetectTitle')}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                      <ul className="list-disc space-y-1 pl-4">
                        <li>{t('explorationDetectOption1')}</li>
                        <li>{t('explorationDetectOption2')}</li>
                        <li>{t('explorationDetectOption3')}</li>
                        <li>{t('explorationDetectOption4')}</li>
                        <li>{t('explorationDetectOption5')}</li>
                      </ul>
                    </CardContent>
                  </Card>

                  <Card className="border-border/70">
                    <CardHeader>
                      <CardTitle className="text-base">{t('explorationHypothesisTitle')}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                      <ul className="list-disc space-y-1 pl-4">
                        <li>{t('explorationHypothesis1')}</li>
                        <li>{t('explorationHypothesis2')}</li>
                        <li>{t('explorationHypothesis3')}</li>
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="ghost"
              onClick={() => setStep((prev) => (prev > 1 ? ((prev - 1) as StepId) : prev))}
              disabled={step === 1}
            >
              {t('previous')}
            </Button>
            {step === 1 && (
              <Button
                onClick={() => setStep(2)}
                disabled={!canContinueToStep2}
                className="gap-2"
              >
                {t('next')}
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
            {step === 2 && (
              <Button
                onClick={handleContinueToStep3}
                disabled={!canContinueToStep3 || status === 'loading'}
                className="gap-2"
              >
                {t('next')}
                <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
