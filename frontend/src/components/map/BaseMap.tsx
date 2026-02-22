import { useEffect } from 'react'
import { MapContainer, TileLayer, ZoomControl, useMap } from 'react-leaflet'
import type { Map as LeafletMap } from 'leaflet'
import { MAP_CONFIG, TILE_LAYERS } from '@/lib/leaflet/config'

type TileLayerKey = keyof typeof TILE_LAYERS

interface BaseMapProps {
  children?: React.ReactNode
  className?: string
  tileLayer?: TileLayerKey
  center?: [number, number]
  zoom?: number
  interactive?: boolean
}

export function BaseMap({
  children,
  className = 'h-full w-full',
  tileLayer = 'light',
  center,
  zoom,
  interactive = true,
}: BaseMapProps) {
  const tiles = TILE_LAYERS[tileLayer]

  return (
    <MapContainer
      center={center ?? MAP_CONFIG.center}
      zoom={zoom ?? MAP_CONFIG.zoom}
      minZoom={MAP_CONFIG.minZoom}
      maxZoom={MAP_CONFIG.maxZoom}
      maxBounds={MAP_CONFIG.maxBounds}
      zoomControl={false}
      scrollWheelZoom={interactive}
      dragging={interactive}
      doubleClickZoom={interactive}
      touchZoom={interactive}
      keyboard={interactive}
      className={className}
    >
      <TileLayer url={tiles.url} attribution={tiles.attribution} />
      <ZoomControl position="bottomright" />
      <CypressMapRegistrar />
      {children}
    </MapContainer>
  )
}

function CypressMapRegistrar() {
  const map = useMap()

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (!(window as typeof window & { Cypress?: boolean }).Cypress) return

    ;(window as typeof window & { __leafletMap?: LeafletMap }).__leafletMap = map

    return () => {
      const win = window as typeof window & { __leafletMap?: LeafletMap }
      if (win.__leafletMap === map) {
        delete win.__leafletMap
      }
    }
  }, [map])

  return null
}
