import { useCallback, useEffect, useRef, useState } from 'react'
import { Marker, Popup, useMap } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import L from 'leaflet'
import type { FireMapItem } from '@/types/map'
import { RETURN_CONTEXT_KEY } from '@/types/navigation'
import { FirePopupCard } from '@/components/map/FirePopupCard'

export type FireMarkersPopupVariant = 'default' | 'fire_detail'

interface FireMarkersProps {
  fires: FireMapItem[]
  selectedFireId?: string | null
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

export function FireMarkers({
  fires,
  selectedFireId = null,
  onFireSelect,
  popupVariant = 'default',
}: FireMarkersProps) {
  const navigate = useNavigate()
  const map = useMap()
  const markerRefs = useRef<Record<string, L.Marker>>({})
  const rafRef = useRef<number | null>(null)
  const [popupLayout, setPopupLayout] = useState({ maxHeight: 240, maxWidth: 320, compact: false })

  const updatePopupLayout = useCallback(() => {
    const container = map.getContainer()
    const mapHeight = container.clientHeight
    const mapWidth = container.clientWidth

    const next = {
      maxHeight: Math.max(140, Math.floor(mapHeight - 80)),
      maxWidth: Math.max(220, Math.min(360, Math.floor(mapWidth - 24))),
      compact: mapWidth <= 1024,
    }

    setPopupLayout((prev) =>
      prev.maxHeight === next.maxHeight && prev.maxWidth === next.maxWidth && prev.compact === next.compact
        ? prev
        : next,
    )
  }, [map])

  useEffect(() => {
    const scheduleUpdate = () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
      }
      rafRef.current = requestAnimationFrame(() => {
        updatePopupLayout()
        rafRef.current = null
      })
    }

    scheduleUpdate()
    map.on('resize moveend zoomend popupopen', scheduleUpdate)
    window.addEventListener('resize', scheduleUpdate)
    window.addEventListener('orientationchange', scheduleUpdate)

    return () => {
      map.off('resize moveend zoomend popupopen', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
      window.removeEventListener('orientationchange', scheduleUpdate)
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
      }
    }
  }, [map, updatePopupLayout])

  useEffect(() => {
    if (!selectedFireId) return
    const marker = markerRefs.current[selectedFireId]
    if (marker?.openPopup) {
      marker.openPopup()
    }
  }, [selectedFireId])

  if (!fires.length) return null

  return (
    <>
      {fires.map((fire) => {
        const detailId = fire.representative_event_id ?? fire.id
        return (
          <Marker
            key={fire.id}
            ref={(el) => {
              if (el) {
                markerRefs.current[fire.id] = el as unknown as L.Marker
              }
            }}
            position={[fire.lat, fire.lon]}
            icon={createFireIcon(fire.severity)}
            eventHandlers={{
              click: () => onFireSelect?.(fire),
            }}
          >
            <Popup
              className="fire-detail-popup"
              autoPan
              keepInView
              closeButton
              autoPanPaddingTopLeft={L.point(20, 20)}
              autoPanPaddingBottomRight={L.point(20, 20)}
              maxWidth={popupLayout.maxWidth}
              minWidth={220}
              maxHeight={popupLayout.maxHeight}
            >
              <FirePopupCard
                fire={fire}
                variant={popupVariant}
                compact={popupLayout.compact}
                maxBodyHeight={popupLayout.maxHeight}
                onViewDetails={
                  popupVariant === 'default'
                    ? () => {
                      const ctx = { returnTo: 'map' as const, map: { selectedFireId: fire.id } }
                      sessionStorage.setItem(RETURN_CONTEXT_KEY, JSON.stringify(ctx))
                      navigate(`/fires/${detailId}`, { state: ctx })
                    }
                    : undefined
                }
              />
            </Popup>
          </Marker>
        )
      })}
    </>
  )
}
