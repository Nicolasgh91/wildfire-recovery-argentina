import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { cellToBoundary } from 'h3-js'
import { getHeatmapColor } from '@/lib/leaflet/styles'

export type H3HeatmapCell = {
  h3Index: string
  intensity: number
  [key: string]: unknown
}

interface H3HeatmapLayerProps {
  cells: H3HeatmapCell[]
  visible?: boolean
}

const closeRing = (coords: [number, number][]) => {
  if (coords.length < 3) return coords
  const [firstLng, firstLat] = coords[0]
  const [lastLng, lastLat] = coords[coords.length - 1]
  if (firstLng === lastLng && firstLat === lastLat) return coords
  return [...coords, coords[0]]
}

export function H3HeatmapLayer({ cells, visible = true }: H3HeatmapLayerProps) {
  const map = useMap()
  const layerRef = useRef<any>(null)

  useEffect(() => {
    let active = true

    const cleanup = () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current)
        layerRef.current = null
      }
    }

    if (!visible || cells.length === 0) {
      cleanup()
      return () => undefined
    }

    const load = async () => {
      await import('leaflet.glify')
      if (!active) return

      const glify = (L as unknown as { glify?: any }).glify
      if (!glify?.shapes) return

      cleanup()

      const features = cells
        .filter((cell) => Boolean(cell.h3Index))
        .map((cell) => ({
          type: 'Feature',
          properties: {
            intensity: Math.max(0, Math.min(1, cell.intensity ?? 0)),
          },
          geometry: {
            type: 'Polygon',
            coordinates: [closeRing(cellToBoundary(cell.h3Index, true))],
          },
        }))

      layerRef.current = glify.shapes({
        map,
        data: {
          type: 'FeatureCollection',
          features,
        },
        color: (_index: number, feature: any) => {
          const intensity = feature?.properties?.intensity ?? 0
          const [r, g, b, a] = getHeatmapColor(intensity)
          return { r: r / 255, g: g / 255, b: b / 255, a: a / 255 }
        },
      })
    }

    void load()

    return () => {
      active = false
      cleanup()
    }
  }, [map, cells, visible])

  return null
}
