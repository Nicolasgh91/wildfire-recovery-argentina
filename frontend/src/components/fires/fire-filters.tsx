import { useCallback, useEffect, useRef, useState } from 'react'
import { Search, Download, Filter, X } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import type { FireFiltersState } from '@/types/fire'
import { cn } from '@/lib/utils'

const DEBOUNCE_MS = 350

const PROVINCES = [
  'Buenos Aires',
  'Catamarca',
  'Chaco',
  'Chubut',
  'Cordoba',
  'Corrientes',
  'Entre Rios',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuquen',
  'Rio Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucuman',
]

const SORT_OPTIONS = [
  { value: 'start_date_desc', label: 'Fecha (mas reciente)' },
  { value: 'start_date_asc', label: 'Fecha (mas antigua)' },
  { value: 'area_desc', label: 'Area (mayor a menor)' },
  { value: 'area_asc', label: 'Area (menor a mayor)' },
  { value: 'frp_desc', label: 'Severidad (mayor a menor)' },
  { value: 'frp_asc', label: 'Severidad (menor a mayor)' },
]

const STATUS_OPTIONS = [
  { value: 'active', label: 'Activos' },
  { value: 'historical', label: 'Historico' },
  { value: 'all', label: 'Todos' },
]

const BOOL_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'true', label: 'Si' },
  { value: 'false', label: 'No' },
]

function filtersEqualDefault(
  filters: FireFiltersState,
  defaultFilters: FireFiltersState
): boolean {
  const keys = Object.keys(defaultFilters) as (keyof FireFiltersState)[]
  return keys.every((k) => {
    const a = filters[k]
    const b = defaultFilters[k]
    if (a === b) return true
    if (a == null && b == null) return true
    if (typeof a === 'number' && typeof b === 'number' && Number.isNaN(a) && Number.isNaN(b))
      return true
    return false
  })
}

interface FireFiltersProps {
  filters: FireFiltersState
  onFiltersChange: (filters: Partial<FireFiltersState>) => void
  onExportCSV: () => void
  isExporting?: boolean
  defaultStatusScope?: FireFiltersState['status_scope']
  defaultFilters: FireFiltersState
  showExportButton?: boolean
}

export function FireFilters({
  filters,
  onFiltersChange,
  onExportCSV,
  isExporting = false,
  defaultStatusScope = 'active',
  defaultFilters,
  showExportButton = true,
}: FireFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [departmentInput, setDepartmentInput] = useState(filters.department)
  const [minConfidenceInput, setMinConfidenceInput] = useState(
    filters.min_confidence != null ? String(filters.min_confidence) : ''
  )
  const [minDetectionsInput, setMinDetectionsInput] = useState(
    filters.min_detections != null ? String(filters.min_detections) : ''
  )
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setDepartmentInput(filters.department)
    setMinConfidenceInput(
      filters.min_confidence != null ? String(filters.min_confidence) : ''
    )
    setMinDetectionsInput(
      filters.min_detections != null ? String(filters.min_detections) : ''
    )
  }, [filters.department, filters.min_confidence, filters.min_detections])

  const flushDebounced = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
      debounceRef.current = null
    }
  }, [])

  useEffect(() => {
    return flushDebounced
  }, [flushDebounced])

  const applyDebounced = useCallback(
    (updates: Partial<FireFiltersState>) => {
      flushDebounced()
      debounceRef.current = setTimeout(() => {
        debounceRef.current = null
        onFiltersChange({ ...updates, page: 1 })
      }, DEBOUNCE_MS)
    },
    [onFiltersChange, flushDebounced]
  )

  const handleReset = () => {
    flushDebounced()
    onFiltersChange({
      ...defaultFilters,
      page: 1,
    })
  }

  const hasActiveFilters = !filtersEqualDefault(filters, defaultFilters)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por ubicación o ID de evento"
            value={filters.search}
            onChange={(e) => onFiltersChange({ search: e.target.value, page: 1 })}
            className="h-9 py-2 pl-10"
          />
        </div>

        <Select
          value={filters.province || 'all'}
          onValueChange={(value) =>
            onFiltersChange({ province: value === 'all' ? '' : value, page: 1 })
          }
        >
          <SelectTrigger className="w-[180px] bg-gray-50 dark:bg-input/30" data-testid="province-filter">
            <SelectValue placeholder="Provincia" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las provincias</SelectItem>
            {PROVINCES.map((province) => (
              <SelectItem key={province} value={province}>
                {province}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.status_scope}
          onValueChange={(value) =>
            onFiltersChange({
              status_scope: value as FireFiltersState['status_scope'],
              page: 1,
            })
          }
        >
          <SelectTrigger className="w-[160px] bg-gray-50 dark:bg-input/30" data-testid="status-filter">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.sort_by}
          onValueChange={(value) =>
            onFiltersChange({ sort_by: value as FireFiltersState['sort_by'] })
          }
        >
          <SelectTrigger className="w-[200px] bg-gray-50 dark:bg-input/30">
            <SelectValue placeholder="Ordenar por" />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="icon"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={cn(
            'bg-gray-50 dark:bg-input/30',
            showAdvanced ? 'bg-emerald-100 text-emerald-700' : ''
          )}
        >
          <Filter className="h-4 w-4" />
        </Button>

        {showExportButton && (
          <Button
            variant="outline"
            onClick={onExportCSV}
            disabled={isExporting}
            className="gap-2 bg-gray-50 dark:bg-input/30"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exportando...' : 'Exportar CSV'}
          </Button>
        )}
      </div>

      {showAdvanced && (
        <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-muted/30 p-4">
          <div className="space-y-2">
            <Label htmlFor="date_from" className="text-sm">
              Fecha desde
            </Label>
            <Input
              id="date_from"
              type="date"
              value={filters.date_from}
              onChange={(e) => onFiltersChange({ date_from: e.target.value, page: 1 })}
              className="w-[160px]"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="date_to" className="text-sm">
              Fecha hasta
            </Label>
            <Input
              id="date_to"
              type="date"
              value={filters.date_to}
              onChange={(e) => onFiltersChange({ date_to: e.target.value, page: 1 })}
              className="w-[160px]"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_department" className="text-sm">
              Departamento
            </Label>
            <Input
              id="filter_department"
              type="text"
              placeholder="Nombre o parte"
              value={departmentInput}
              onChange={(e) => {
                setDepartmentInput(e.target.value)
                applyDebounced({ department: e.target.value })
              }}
              className="w-[180px]"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_in_protected" className="text-sm">
              En área protegida
            </Label>
            <Select
              value={
                filters.in_protected_area === true
                  ? 'true'
                  : filters.in_protected_area === false
                    ? 'false'
                    : 'all'
              }
              onValueChange={(v) =>
                onFiltersChange({
                  in_protected_area:
                    v === 'true' ? true : v === 'false' ? false : undefined,
                  page: 1,
                })
              }
            >
              <SelectTrigger id="filter_in_protected" className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BOOL_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_significant" className="text-sm">
              Significativo
            </Label>
            <Select
              value={
                filters.is_significant === true
                  ? 'true'
                  : filters.is_significant === false
                    ? 'false'
                    : 'all'
              }
              onValueChange={(v) =>
                onFiltersChange({
                  is_significant:
                    v === 'true' ? true : v === 'false' ? false : undefined,
                  page: 1,
                })
              }
            >
              <SelectTrigger id="filter_significant" className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BOOL_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_imagery" className="text-sm">
              Con imágenes satelitales
            </Label>
            <Select
              value={
                filters.has_imagery === true
                  ? 'true'
                  : filters.has_imagery === false
                    ? 'false'
                    : 'all'
              }
              onValueChange={(v) =>
                onFiltersChange({
                  has_imagery:
                    v === 'true' ? true : v === 'false' ? false : undefined,
                  page: 1,
                })
              }
            >
              <SelectTrigger id="filter_imagery" className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {BOOL_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_min_confidence" className="text-sm">
              Confianza mín. (%)
            </Label>
            <Input
              id="filter_min_confidence"
              type="number"
              min={0}
              max={100}
              placeholder="Ej. 50"
              value={minConfidenceInput}
              onChange={(e) => {
                setMinConfidenceInput(e.target.value)
                const n = e.target.value === '' ? undefined : Number(e.target.value)
                applyDebounced({
                  min_confidence:
                    n != null && Number.isFinite(n) && n >= 0 ? n : undefined,
                })
              }}
              className="w-[100px]"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="filter_min_detections" className="text-sm">
              Detecciones mín.
            </Label>
            <Input
              id="filter_min_detections"
              type="number"
              min={0}
              placeholder="Ej. 5"
              value={minDetectionsInput}
              onChange={(e) => {
                setMinDetectionsInput(e.target.value)
                const n = e.target.value === '' ? undefined : Number(e.target.value)
                applyDebounced({
                  min_detections:
                    n != null && Number.isFinite(n) && n >= 0 ? Math.floor(n) : undefined,
                })
              }}
              className="w-[100px]"
            />
          </div>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="gap-1 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
              Limpiar filtros
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
