import { Marker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import L from 'leaflet'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import type { FireMapItem } from '@/types/map'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'

export type FireMarkersPopupVariant = 'default' | 'fire_detail'

interface FireMarkersProps {
  fires: FireMapItem[]
  onFireSelect?: (fire: FireMapItem) => void
  popupVariant?: FireMarkersPopupVariant
}

const markerColors: Record<NonNullable<FireMapItem['severity']>, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#10b981',
}

function createFireIcon(severity?: FireMapItem['severity']) {
  const safeSeverity = severity ?? 'low'
  const color = markerColors[safeSeverity]

  return L.divIcon({
    className: 'custom-fire-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="white" stroke="white" strokeWidth="2">
          <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
        </svg>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  })
}

export function FireMarkers({ fires, onFireSelect, popupVariant = 'default' }: FireMarkersProps) {
  const { t } = useI18n()
  const navigate = useNavigate()

  if (!fires.length) return null

  return (
    <>
      {fires.map((fire) => {
        const detailId = fire.representative_event_id ?? fire.id
        return (
          <Marker
            key={fire.id}
            position={[fire.lat, fire.lon]}
            icon={createFireIcon(fire.severity)}
            eventHandlers={{
              click: () => onFireSelect?.(fire),
            }}
          >
            <Popup>
              {popupVariant === 'fire_detail' ? (
                <div className="min-w-[220px] p-2">
                  <h3 className="mb-2 font-semibold">
                    {fire.status === 'monitoring'
                      ? t('firePopupTitleMonitoring')
                      : fire.status === 'controlled'
                        ? t('firePopupTitleControlled')
                        : fire.status === 'extinguished'
                          ? t('firePopupTitleExtinguished')
                          : t('firePopupTitleActive')}
                  </h3>
                  <div className="mb-3 flex flex-wrap gap-2">
                    <Badge
                      variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
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
                    <p>
                      {t('province')}: {fire.province || 'N/A'}
                    </p>
                    <p>
                      {t('popupProtectedAreaPercentage')}:{' '}
                      {fire.in_protected_area &&
                        fire.overlap_percentage !== null &&
                        fire.overlap_percentage !== undefined
                        ? `${fire.overlap_percentage.toFixed(1)}%`
                        : 'N/A'}
                    </p>
                    <p>
                      {t('popupProtectedAreas')}:{' '}
                      {fire.in_protected_area && fire.protected_area_name ? fire.protected_area_name : 'N/A'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="min-w-[200px] p-2">
                  <h3 className="mb-2 font-semibold">{fire.title}</h3>
                  <div className="mb-3 flex flex-wrap gap-2">
                    <Badge
                      variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                      className="text-xs"
                    >
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
                  <div className="mb-3 space-y-1 text-sm text-muted-foreground">
                    <p>
                      {t('area')}:{' '}
                      {fire.hectares !== null && fire.hectares !== undefined
                        ? fire.hectares.toLocaleString()
                        : 'N/A'}{' '}
                      ha
                    </p>
                    <p>
                      {t('province')}: {fire.province || 'N/A'}
                    </p>
                    {fire.overlap_percentage !== null &&
                      fire.overlap_percentage !== undefined &&
                      fire.in_protected_area && (
                        <p>
                          {t('protectedArea')}: {fire.overlap_percentage.toFixed(1)}%
                        </p>
                      )}
                    {fire.in_protected_area && fire.protected_area_name && (
                      <p>
                        {t('protectedArea')}: {fire.protected_area_name}
                      </p>
                    )}
                    {fire.in_protected_area &&
                      fire.count_protected_areas !== null &&
                      fire.count_protected_areas !== undefined && (
                        <p>
                          {t('protectedArea')}: {fire.count_protected_areas}
                        </p>
                      )}
                  </div>
                  <Button size="sm" className="w-full" onClick={() => {
                    const ctx = { returnTo: 'map' as const, map: { selectedFireId: fire.id } }
                    sessionStorage.setItem(RETURN_CONTEXT_KEY, JSON.stringify(ctx))
                    navigate(`/fires/${detailId}`, { state: ctx })
                  }}>
                    {t('viewDetails')}
                  </Button>
                </div>
              )}
            </Popup>
          </Marker>
        )
      })}
    </>
  )
}
