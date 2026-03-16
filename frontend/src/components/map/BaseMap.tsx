import { useEffect } from 'react'
import { MapContainer, TileLayer, ZoomControl, useMap } from 'react-leaflet'
import type { Map as LeafletMap } from 'leaflet'
import { MAP_CONFIG, TILE_LAYERS } from '@/lib/leaflet/config'
import { useNavigate } from 'react-router-dom'
import { RETURN_CONTEXT_KEY, type ReturnContext } from '@/types/navigation'

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
  const navigate = useNavigate()

  useEffect(() => {
    if (typeof document === 'undefined') return

    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null
      if (!target) return

      const anchor = target.closest('a') as HTMLAnchorElement | null
      if (!anchor) return

      const href = anchor.getAttribute('href')
      if (!href || !href.startsWith('/fires/')) return

      // Solo interceptar enlaces internos a /fires/:id
      event.preventDefault()

      const url = new URL(href, window.location.origin)
      const parts = url.pathname.split('/')
      const detailId = parts[2] || ''

      const ctx: ReturnContext = { returnTo: 'map', map: { selectedFireId: detailId } }
      try {
        sessionStorage.setItem(RETURN_CONTEXT_KEY, JSON.stringify(ctx))
      } catch {
        // ignore storage errors
      }

      navigate(url.pathname + url.search, { state: ctx })
    }

    document.addEventListener('click', handleClick)
    return () => {
      document.removeEventListener('click', handleClick)
    }
  }, [navigate])

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
