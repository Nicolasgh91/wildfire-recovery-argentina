'use client'

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { PaginationMeta } from '@/types/fire'

interface PaginationProps {
  pagination: PaginationMeta
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

const PAGE_SIZE_OPTIONS = [12, 24, 48, 96]

export function Pagination({
  pagination,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const { page, total_pages, total, page_size } = pagination

  const canGoPrevious = page > 1
  const canGoNext = page < total_pages

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | string)[] = []
    const maxVisible = 5

    if (total_pages <= maxVisible) {
      for (let i = 1; i <= total_pages; i++) {
        pages.push(i)
      }
    } else {
      if (page <= 3) {
        for (let i = 1; i <= 4; i++) pages.push(i)
        pages.push('...')
        pages.push(total_pages)
      } else if (page >= total_pages - 2) {
        pages.push(1)
        pages.push('...')
        for (let i = total_pages - 3; i <= total_pages; i++) pages.push(i)
      } else {
        pages.push(1)
        pages.push('...')
        for (let i = page - 1; i <= page + 1; i++) pages.push(i)
        pages.push('...')
        pages.push(total_pages)
      }
    }

    return pages
  }

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      {/* Results Info */}
      <p className="text-sm text-muted-foreground">
        Mostrando{' '}
        <span className="font-medium text-foreground">
          {(page - 1) * page_size + 1}
        </span>{' '}
        a{' '}
        <span className="font-medium text-foreground">
          {Math.min(page * page_size, total)}
        </span>{' '}
        de <span className="font-medium text-foreground">{total}</span> incendios
      </p>

      <div className="flex items-center gap-4">
        {/* Page Size Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Por página:</span>
          <Select
            value={page_size.toString()}
            onValueChange={(value) => onPageSizeChange(Number(value))}
          >
            <SelectTrigger className="w-[70px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PAGE_SIZE_OPTIONS.map((size) => (
                <SelectItem key={size} value={size.toString()}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Page Navigation */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(1)}
            disabled={!canGoPrevious}
            className="h-8 w-8"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(page - 1)}
            disabled={!canGoPrevious}
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {/* Page Numbers */}
          <div className="flex items-center gap-1">
            {getPageNumbers().map((pageNum, idx) =>
              pageNum === '...' ? (
                <span
                  key={`ellipsis-${idx}`}
                  className="px-2 text-muted-foreground"
                >
                  ...
                </span>
              ) : (
                <Button
                  key={pageNum}
                  variant={pageNum === page ? 'default' : 'outline'}
                  size="icon"
                  onClick={() => onPageChange(pageNum as number)}
                  className={`h-8 w-8 ${
                    pageNum === page
                      ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                      : ''
                  }`}
                >
                  {pageNum}
                </Button>
              )
            )}
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(page + 1)}
            disabled={!canGoNext}
            className="h-8 w-8"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(total_pages)}
            disabled={!canGoNext}
            className="h-8 w-8"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
