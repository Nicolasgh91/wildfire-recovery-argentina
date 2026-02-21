import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import type { FireMapItem } from '@/types/map'

interface FirePopupCardProps {
  fire: FireMapItem
  variant: 'default' | 'fire_detail'
  maxBodyHeight: number
  compact?: boolean
  onViewDetails?: () => void
}

export function FirePopupCard({
  fire,
  variant,
  maxBodyHeight,
  compact = false,
  onViewDetails,
}: FirePopupCardProps) {
  const { t } = useI18n()

  if (variant === 'fire_detail') {
    return (
      <div
        data-testid="fire-popup-card"
        className="min-w-[220px]"
      >
        <div
          data-testid="fire-popup-scroll"
          className="space-y-2 overflow-y-auto pr-1"
          style={{ maxHeight: `${maxBodyHeight}px` }}
        >
          <h3 className="font-semibold">
            {fire.status === 'monitoring'
              ? t('firePopupTitleMonitoring')
              : fire.status === 'controlled'
                ? t('firePopupTitleControlled')
                : fire.status === 'extinguished'
                  ? t('firePopupTitleExtinguished')
                  : t('firePopupTitleActive')}
          </h3>
          <div className="flex flex-wrap gap-2">
            <Badge variant={fire.severity === 'high' ? 'destructive' : 'secondary'} className="text-xs">
              {fire.severity === 'high'
                ? t('severityHigh')
                : fire.severity === 'medium'
                  ? t('severityMedium')
                  : t('severityLow')}
            </Badge>
            {fire.in_protected_area && (
              <Badge variant="outline" className="border-emerald-200 bg-emerald-100 text-emerald-700">
                {t('protectedAreaLabel')}
              </Badge>
            )}
          </div>
          <div className="space-y-0 text-sm text-muted-foreground [&>p]:m-0">
            <p>{t('province')}: {fire.province || 'N/A'}</p>
            <p>
              {t('popupProtectedAreaPercentage')}: {' '}
              {fire.in_protected_area && fire.overlap_percentage !== null && fire.overlap_percentage !== undefined
                ? `${fire.overlap_percentage.toFixed(1)}%`
                : 'N/A'}
            </p>
            <p>
              {t('popupProtectedAreas')}: {' '}
              {fire.in_protected_area && fire.protected_area_name ? fire.protected_area_name : 'N/A'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="fire-popup-card" className="min-w-[200px]">
      <div
        data-testid="fire-popup-scroll"
        className="space-y-2 overflow-y-auto pr-1"
        style={{ maxHeight: `${maxBodyHeight}px` }}
      >
        <h3 className="font-semibold">{fire.title}</h3>
        <div className="flex flex-wrap gap-2">
          <Badge variant={fire.severity === 'high' ? 'destructive' : 'secondary'} className="text-xs">
            {fire.severity === 'high'
              ? t('highSeverity')
              : fire.severity === 'medium'
                ? t('mediumSeverity')
                : t('lowSeverity')}
          </Badge>
          {fire.in_protected_area && (
            <Badge variant="outline" className="border-emerald-200 bg-emerald-100 text-emerald-700">
              {t('protectedArea')}
            </Badge>
          )}
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            {t('area')}: {fire.hectares !== null && fire.hectares !== undefined ? fire.hectares.toLocaleString() : 'N/A'} ha
          </p>
          <p>{t('province')}: {fire.province || 'N/A'}</p>
          {fire.overlap_percentage !== null && fire.overlap_percentage !== undefined && fire.in_protected_area && (
            <p>{t('protectedArea')}: {fire.overlap_percentage.toFixed(1)}%</p>
          )}
          {fire.in_protected_area && fire.protected_area_name && (
            <p>{t('protectedArea')}: {fire.protected_area_name}</p>
          )}
          {fire.in_protected_area && fire.count_protected_areas !== null && fire.count_protected_areas !== undefined && (
            <p>{t('protectedArea')}: {fire.count_protected_areas}</p>
          )}
        </div>
      </div>
      <Button
        size="sm"
        className={`mt-3 w-full ${compact ? 'sticky bottom-0' : ''}`}
        onClick={onViewDetails}
      >
        {t('viewDetails')}
      </Button>
    </div>
  )
}
