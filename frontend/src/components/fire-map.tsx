import { useMemo } from 'react'
import { MapView } from '@/components/map/MapView'
import type { FireMapItem } from '@/types/map'
import type { FireMarkersPopupVariant } from '@/components/map/layers/FireMarkers'

interface FireMapProps {
  fires: FireMapItem[]
  selectedFire?: FireMapItem | null
  onFireSelect?: (fire: FireMapItem) => void
  height?: string
  interactive?: boolean
  popupVariant?: FireMarkersPopupVariant
}

export function FireMap({ 
  fires, 
  selectedFire, 
  onFireSelect, 
  height = 'h-[calc(100vh-8rem)]',
  interactive = true,
  popupVariant = 'default',
}: FireMapProps) {
  const safeCenter = useMemo(() => {
    if (!selectedFire) return undefined
    const center: [number, number] = [selectedFire.lat, selectedFire.lon]
    return Number.isFinite(center[0]) && Number.isFinite(center[1]) ? center : undefined
  }, [selectedFire])

  return (
    <div className={`${height} w-full overflow-hidden rounded-lg border border-border isolate`}>
      <MapView
        fires={fires}
        center={safeCenter}
        interactive={interactive}
        className="h-full w-full"
        onFireSelect={onFireSelect}
        popupVariant={popupVariant}
      />
    </div>
  )
}
