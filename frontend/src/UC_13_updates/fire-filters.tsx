'use client'

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
import { Switch } from '@/components/ui/switch'
import type { FireFiltersState } from '@/types/fire'

// Argentine provinces
const PROVINCES = [
  'Buenos Aires',
  'Catamarca',
  'Chaco',
  'Chubut',
  'Córdoba',
  'Corrientes',
  'Entre Ríos',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuquén',
  'Río Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucumán',
]

const SORT_OPTIONS = [
  { value: 'start_date_desc', label: 'Fecha (más reciente)' },
  { value: 'start_date_asc', label: 'Fecha (más antiguo)' },
  { value: 'area_desc', label: 'Área (mayor a menor)' },
  { value: 'area_asc', label: 'Área (menor a mayor)' },
  { value: 'frp_desc', label: 'Severidad (mayor a menor)' },
  { value: 'frp_asc', label: 'Severidad (menor a mayor)' },
]

interface FireFiltersProps {
  filters: FireFiltersState
  onFiltersChange: (filters: Partial<FireFiltersState>) => void
  onExportCSV: () => void
  isExporting?: boolean
}

export function FireFilters({
  filters,
  onFiltersChange,
  onExportCSV,
  isExporting = false,
}: FireFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleReset = () => {
    onFiltersChange({
      province: '',
      active_only: false,
      date_from: '',
      date_to: '',
      search: '',
      sort_by: 'start_date_desc',
      page: 1,
    })
  }

  const hasActiveFilters =
    filters.province ||
    filters.active_only ||
    filters.date_from ||
    filters.date_to ||
    filters.search

  return (
    <div className="space-y-4">
      {/* Main Filter Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por ubicación..."
            value={filters.search}
            onChange={(e) => onFiltersChange({ search: e.target.value, page: 1 })}
            className="pl-10"
          />
        </div>

        {/* Province Select */}
        <Select
          value={filters.province || 'all'}
          onValueChange={(value) =>
            onFiltersChange({ province: value === 'all' ? '' : value, page: 1 })
          }
        >
          <SelectTrigger className="w-[180px]">
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

        {/* Sort Select */}
        <Select
          value={filters.sort_by}
          onValueChange={(value) => onFiltersChange({ sort_by: value })}
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

        {/* Toggle Advanced Filters */}
        <Button
          variant="outline"
          size="icon"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={showAdvanced ? 'bg-emerald-100 text-emerald-700' : ''}
        >
          <Filter className="h-4 w-4" />
        </Button>

        {/* Export CSV Button */}
        <Button
          variant="outline"
          onClick={onExportCSV}
          disabled={isExporting}
          className="gap-2 bg-transparent"
        >
          <Download className="h-4 w-4" />
          {isExporting ? 'Exportando...' : 'Exportar CSV'}
        </Button>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-muted/30 p-4">
          {/* Date From */}
          <div className="space-y-2">
            <Label htmlFor="date_from" className="text-sm">
              Fecha desde
            </Label>
            <Input
              id="date_from"
              type="date"
              value={filters.date_from}
              onChange={(e) =>
                onFiltersChange({ date_from: e.target.value, page: 1 })
              }
              className="w-[160px]"
            />
          </div>

          {/* Date To */}
          <div className="space-y-2">
            <Label htmlFor="date_to" className="text-sm">
              Fecha hasta
            </Label>
            <Input
              id="date_to"
              type="date"
              value={filters.date_to}
              onChange={(e) =>
                onFiltersChange({ date_to: e.target.value, page: 1 })
              }
              className="w-[160px]"
            />
          </div>

          {/* Active Only Toggle */}
          <div className="flex items-center gap-2 pb-2">
            <Switch
              id="active_only"
              checked={filters.active_only}
              onCheckedChange={(checked) =>
                onFiltersChange({ active_only: checked, page: 1 })
              }
            />
            <Label htmlFor="active_only" className="text-sm cursor-pointer">
              Solo activos
            </Label>
          </div>

          {/* Reset Filters */}
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
