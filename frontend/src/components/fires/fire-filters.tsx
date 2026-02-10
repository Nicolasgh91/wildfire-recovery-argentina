import { useState } from 'react'
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

interface FireFiltersProps {
  filters: FireFiltersState
  onFiltersChange: (filters: Partial<FireFiltersState>) => void
  onExportCSV: () => void
  isExporting?: boolean
  defaultStatusScope?: FireFiltersState['status_scope']
  showExportButton?: boolean
}

export function FireFilters({
  filters,
  onFiltersChange,
  onExportCSV,
  isExporting = false,
  defaultStatusScope = 'active',
  showExportButton = true,
}: FireFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleReset = () => {
    onFiltersChange({
      province: '',
      status_scope: defaultStatusScope,
      date_from: '',
      date_to: '',
      search: '',
      sort_by: 'start_date_desc',
      page: 1,
    })
  }

  const hasActiveFilters =
    filters.province ||
    filters.status_scope !== defaultStatusScope ||
    filters.date_from ||
    filters.date_to ||
    filters.search

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por ubicacion..."
            value={filters.search}
            onChange={(e) => onFiltersChange({ search: e.target.value, page: 1 })}
            className="pl-10"
          />
        </div>

        <Select
          value={filters.province || 'all'}
          onValueChange={(value) =>
            onFiltersChange({ province: value === 'all' ? '' : value, page: 1 })
          }
        >
          <SelectTrigger className="w-[180px]" data-testid="province-filter">
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
          <SelectTrigger className="w-[160px]" data-testid="status-filter">
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
          <SelectTrigger className="w-[200px]">
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
          className={showAdvanced ? 'bg-emerald-100 text-emerald-700' : ''}
        >
          <Filter className="h-4 w-4" />
        </Button>

        {showExportButton && (
          <Button
            variant="outline"
            onClick={onExportCSV}
            disabled={isExporting}
            className="gap-2 bg-transparent"
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
