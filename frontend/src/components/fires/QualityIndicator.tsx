import {
  AlertTriangle,
  CheckCircle2,
  CloudSun,
  Satellite,
  Sigma,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useI18n } from '@/context/LanguageContext'
import { cn } from '@/lib/utils'
import type { QualityClass, QualityResponse } from '@/types/quality'

interface QualityIndicatorProps {
  quality?: QualityResponse | null
  isLoading?: boolean
  error?: unknown
}

const CLASS_STYLES: Record<QualityClass, string> = {
  high: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  medium: 'border-amber-200 bg-amber-100 text-amber-700',
  low: 'border-red-200 bg-red-100 text-red-700',
}

const SCORE_COLORS = {
  high: 'text-emerald-600',
  medium: 'text-amber-600',
  low: 'text-red-600',
}

const PROGRESS_COLORS = {
  high: '[&>div]:bg-emerald-500',
  medium: '[&>div]:bg-amber-500',
  low: '[&>div]:bg-red-500',
}

const resolveClassKey = (value: QualityClass | undefined): QualityClass => {
  if (value === 'high' || value === 'medium' || value === 'low') {
    return value
  }
  return 'low'
}

export function QualityIndicator({ quality, isLoading, error }: QualityIndicatorProps) {
  const { t } = useI18n()

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-3 w-full" />
          <div className="grid gap-3 sm:grid-cols-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
          <Skeleton className="h-8 w-48" />
        </CardContent>
      </Card>
    )
  }

  if (!quality || error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('qualityIndicator')}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {t('qualityUnavailable')}
        </CardContent>
      </Card>
    )
  }

  const classification = resolveClassKey(quality.metrics.classification)
  const classLabel =
    classification === 'high'
      ? t('qualityHigh')
      : classification === 'medium'
      ? t('qualityMedium')
      : t('qualityLow')

  const score = Math.round(quality.metrics.reliability_score)
  const formattedDate = quality.metrics.score_calculated_at
    ? new Date(quality.metrics.score_calculated_at).toLocaleDateString()
    : null

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle>{t('qualityIndicator')}</CardTitle>
          {formattedDate && (
            <p className="text-xs text-muted-foreground">
              {t('qualityUpdatedAt')}: {formattedDate}
            </p>
          )}
        </div>
        <Badge variant="outline" className={cn('border font-medium', CLASS_STYLES[classification])}>
          {t('qualityClassification')}: {classLabel}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Progress value={score} className={cn('h-3', PROGRESS_COLORS[classification])} />
          </div>
          <span className={cn('text-2xl font-bold', SCORE_COLORS[classification])}>
            {score}%
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-muted/40 p-3">
            <p className="text-xs text-muted-foreground">{t('avgConfidence')}</p>
            <p className="text-lg font-semibold">
              {quality.metrics.avg_confidence.toFixed(1)}%
            </p>
          </div>
          <div className="rounded-lg border border-border bg-muted/40 p-3">
            <p className="text-xs text-muted-foreground">{t('detections')}</p>
            <p className="text-lg font-semibold">{quality.metrics.total_detections}</p>
          </div>
          <div className="rounded-lg border border-border bg-muted/40 p-3">
            <p className="text-xs text-muted-foreground">{t('independentSources')}</p>
            <p className="text-lg font-semibold">{quality.metrics.independent_sources}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant={quality.metrics.has_imagery ? 'default' : 'outline'} className="gap-1">
            <Satellite className="h-3 w-3" />
            {t('imagery')}
          </Badge>
          <Badge variant={quality.metrics.has_climate ? 'default' : 'outline'} className="gap-1">
            <CloudSun className="h-3 w-3" />
            {t('climate')}
          </Badge>
          <Badge variant={quality.metrics.has_ndvi ? 'default' : 'outline'} className="gap-1">
            <Sigma className="h-3 w-3" />
            {t('ndvi')}
          </Badge>
        </div>

        {quality.warnings.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            <div className="mb-1 flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              {t('qualityWarnings')}
            </div>
            <ul className="list-disc pl-5">
              {quality.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {quality.warnings.length === 0 && (
          <div className="flex items-center gap-2 text-xs text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            {t('qualityNoWarnings')}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
