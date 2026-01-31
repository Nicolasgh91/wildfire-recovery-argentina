'use client'

import Link from 'next/link'
import { MapPin, Calendar, Ruler, ArrowRight, Flame } from 'lucide-react'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  type FireEventListItem,
  getSeverityConfig,
  formatHectares,
  formatDate,
  getFireTitle,
} from '@/types/fire'
import { cn } from '@/lib/utils'

interface FireCardProps {
  fire: FireEventListItem
}

export function FireCard({ fire }: FireCardProps) {
  const severity = getSeverityConfig(fire.max_frp)
  const title = getFireTitle(fire.department, fire.province)

  return (
    <Card className="overflow-hidden transition-all hover:shadow-lg hover:-translate-y-1">
      {/* Header with gradient background and central icon */}
      <div className="relative aspect-[4/3] bg-gradient-to-br from-emerald-50 via-emerald-100/50 to-amber-50">
        {/* Central Flame Icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-full bg-white/60 p-6 shadow-sm backdrop-blur-sm">
            <Flame className={cn('h-12 w-12', severity.iconColor)} />
          </div>
        </div>

        {/* Severity Badge - Top Left */}
        <Badge
          variant="outline"
          className={cn(
            'absolute left-3 top-3 border font-medium',
            severity.badgeClasses
          )}
        >
          {severity.label}
        </Badge>

        {/* Status Badge - Top Right */}
        <Badge
          variant="outline"
          className={cn(
            'absolute right-3 top-3 border font-medium',
            fire.is_active
              ? 'border-red-200 bg-red-100 text-red-700'
              : 'border-slate-200 bg-slate-100 text-slate-600'
          )}
        >
          {fire.is_active ? 'Activo' : 'Extinguido'}
        </Badge>
      </div>

      {/* Card Body */}
      <CardContent className="p-4">
        <h3 className="mb-3 line-clamp-2 text-lg font-semibold leading-tight text-foreground">
          {title}
        </h3>

        {/* Metadata Row */}
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-emerald-600" />
            {fire.province}
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

      {/* Card Footer */}
      <CardFooter className="border-t border-border bg-muted/30 p-4">
        <Link href={`/fires/${fire.id}`} className="w-full">
          <Button
            className="w-full gap-2 bg-emerald-500 text-white hover:bg-emerald-600"
          >
            Ver Detalles
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardFooter>
    </Card>
  )
}

// Skeleton component for loading state
export function FireCardSkeleton() {
  return (
    <Card className="overflow-hidden">
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
