import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import type { FeatureCollection } from 'geojson'
import { BaseMap } from './BaseMap'
import { FireMarkers } from './layers/FireMarkers'
import { EpisodeLayer, type Episode } from './layers/EpisodeLayer'
import { H3HeatmapLayer, type H3HeatmapCell } from './layers/H3HeatmapLayer'
import { ProtectedAreas, type ProtectedAreaProperties } from './layers/ProtectedAreas'
import type { FireMapItem } from '@/types/map'
import type { FireMarkersPopupVariant } from './layers/FireMarkers'

interface MapViewProps {
  fires?: FireMapItem[]
  selectedFireId?: string | null
  episodes?: Episode[]
  heatmapCells?: H3HeatmapCell[]
  protectedAreas?: FeatureCollection | null
  showHeatmap?: boolean
  showProtectedAreas?: boolean
  tileLayer?: 'light' | 'satellite' | 'terrain'
  className?: string
  center?: [number, number]
  zoom?: number
  interactive?: boolean
  onFireSelect?: (fire: FireMapItem) => void
  onEpisodeSelect?: (episode: Episode) => void
  onProtectedAreaSelect?: (props: ProtectedAreaProperties) => void
  popupVariant?: FireMarkersPopupVariant
}

function MapCenterUpdater({ center }: { center?: [number, number] }) {
  const map = useMap()

  useEffect(() => {
    if (!center) return
    map.setView(center, map.getZoom())
  }, [center, map])

  return null
}

export function MapView({
  fires = [],
  selectedFireId = null,
  episodes = [],
  heatmapCells = [],
  protectedAreas = null,
  showHeatmap = false,
  showProtectedAreas = false,
  tileLayer = 'light',
  className = 'h-full w-full',
  center,
  zoom,
  interactive = true,
  onFireSelect,
  onEpisodeSelect,
  onProtectedAreaSelect,
  popupVariant = 'default',
}: MapViewProps) {
  return (
    <BaseMap className={className} tileLayer={tileLayer} center={center} zoom={zoom} interactive={interactive}>
      <MapCenterUpdater center={center} />
      <FireMarkers
        fires={fires}
        selectedFireId={selectedFireId}
        onFireSelect={onFireSelect}
        popupVariant={popupVariant}
      />
      <EpisodeLayer episodes={episodes} onEpisodeClick={onEpisodeSelect} />
      {showHeatmap && <H3HeatmapLayer cells={heatmapCells} visible={showHeatmap} />}
      {showProtectedAreas && (
        <ProtectedAreas data={protectedAreas} visible={showProtectedAreas} onAreaClick={onProtectedAreaSelect} />
      )}
    </BaseMap>
  )
}
