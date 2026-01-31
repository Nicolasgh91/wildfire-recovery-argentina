'use client'

import { useEffect, useCallback, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import useSWR from 'swr'
import { Trees, AlertTriangle } from 'lucide-react'
import { FireCard, FireCardSkeleton } from '@/components/fires/fire-card'
import { FireFilters } from '@/components/fires/fire-filters'
import { Pagination } from '@/components/fires/pagination'
import type { FireFiltersState, FireListResponse } from '@/types/fire'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

// Default filter values
const DEFAULT_FILTERS: FireFiltersState = {
  province: '',
  active_only: false,
  date_from: '',
  date_to: '',
  search: '',
  sort_by: 'start_date_desc',
  page: 1,
  page_size: 12,
}

// SWR fetcher function
const fetcher = async (url: string): Promise<FireListResponse> => {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('Error al cargar los datos')
  }
  return response.json()
}

// Build query string from filters
function buildQueryString(filters: FireFiltersState): string {
  const params = new URLSearchParams()

  if (filters.province) params.set('province', filters.province)
  if (filters.active_only) params.set('active_only', 'true')
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.search) params.set('search', filters.search)
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  params.set('page', filters.page.toString())
  params.set('page_size', filters.page_size.toString())

  return params.toString()
}

// Parse URL params to filters
function parseUrlParams(searchParams: URLSearchParams): FireFiltersState {
  return {
    province: searchParams.get('province') || '',
    active_only: searchParams.get('active_only') === 'true',
    date_from: searchParams.get('date_from') || '',
    date_to: searchParams.get('date_to') || '',
    search: searchParams.get('search') || '',
    sort_by: searchParams.get('sort_by') || 'start_date_desc',
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || 12,
  }
}

function FireGridContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const filters = parseUrlParams(searchParams)

  // Build API URL
  const apiUrl = `${API_BASE_URL}/fires?${buildQueryString(filters)}`

  // Fetch data with SWR
  const { data, error, isLoading, mutate } = useSWR<FireListResponse>(
    apiUrl,
    fetcher,
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  )

  // Update URL when filters change
  const updateFilters = useCallback(
    (newFilters: Partial<FireFiltersState>) => {
      const updatedFilters = { ...filters, ...newFilters }
      const queryString = buildQueryString(updatedFilters)
      router.push(`/fires?${queryString}`, { scroll: false })
    },
    [filters, router]
  )

  // Handle CSV export
  const handleExportCSV = useCallback(async () => {
    try {
      const exportUrl = `${API_BASE_URL}/fires/export?${buildQueryString(filters)}`
      const response = await fetch(exportUrl)

      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `incendios_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export error:', err)
    }
  }, [filters])

  // Handle pagination
  const handlePageChange = (page: number) => {
    updateFilters({ page })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handlePageSizeChange = (pageSize: number) => {
    updateFilters({ page_size: pageSize, page: 1 })
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-lg bg-emerald-100 p-2">
              <Trees className="h-8 w-8 text-emerald-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                Registro de Incendios
              </h1>
              <p className="text-sm text-muted-foreground">
                {data ? (
                  <>
                    {data.pagination.total} incendios encontrados
                  </>
                ) : (
                  'Cargando...'
                )}
              </p>
            </div>
          </div>

          {/* Filters */}
          <FireFilters
            filters={filters}
            onFiltersChange={updateFilters}
            onExportCSV={handleExportCSV}
          />
        </div>

        {/* Error State */}
        {error && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10 p-8 text-center">
            <AlertTriangle className="mb-4 h-12 w-12 text-destructive" />
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              Error al cargar los datos
            </h3>
            <p className="mb-4 text-muted-foreground">
              No se pudieron cargar los incendios. Por favor, intente de nuevo.
            </p>
            <button
              onClick={() => mutate()}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-white hover:bg-emerald-600"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Loading State - Skeleton Grid */}
        {isLoading && !data && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <FireCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Fire Grid */}
        {data && data.data.length > 0 && (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {data.data.map((fire) => (
                <FireCard key={fire.id} fire={fire} />
              ))}
            </div>

            {/* Pagination */}
            <div className="mt-8 border-t border-border pt-6">
              <Pagination
                pagination={data.pagination}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            </div>
          </>
        )}

        {/* Empty State */}
        {data && data.data.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 rounded-full bg-muted p-6">
              <Trees className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              No se encontraron incendios
            </h3>
            <p className="text-muted-foreground">
              Intente ajustar los filtros de búsqueda
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// Main page with Suspense boundary for useSearchParams
export default function FireGridPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background">
          <div className="container mx-auto px-4 py-6">
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-12 w-12 animate-pulse rounded-lg bg-muted" />
                <div>
                  <div className="h-6 w-48 animate-pulse rounded bg-muted mb-2" />
                  <div className="h-4 w-32 animate-pulse rounded bg-muted" />
                </div>
              </div>
            </div>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <FireCardSkeleton key={i} />
              ))}
            </div>
          </div>
        </div>
      }
    >
      <FireGridContent />
    </Suspense>
  )
}
