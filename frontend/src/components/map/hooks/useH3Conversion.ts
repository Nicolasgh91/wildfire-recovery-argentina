import { useMemo } from 'react'
import { cellToBoundary, cellToLatLng } from 'h3-js'
import type { FeatureCollection, Feature, Polygon, Point } from 'geojson'

export type H3Cell = {
  h3Index: string
  intensity?: number
  [key: string]: unknown
}

type UseH3ConversionOptions = {
  asPolygons?: boolean
}

const closeRing = (coords: [number, number][]) => {
  if (coords.length < 3) return coords
  const [firstLng, firstLat] = coords[0]
  const [lastLng, lastLat] = coords[coords.length - 1]
  if (firstLng === lastLng && firstLat === lastLat) return coords
  return [...coords, coords[0]]
}

export function useH3Conversion(
  cells: H3Cell[],
  options: UseH3ConversionOptions = { asPolygons: true }
) {
  const usePolygons = options.asPolygons ?? true

  return useMemo(() => {
    if (!cells || cells.length === 0) {
      return {
        type: 'FeatureCollection',
        features: [],
      } as FeatureCollection
    }

    const features: Feature[] = cells.map((cell) => {
      if (usePolygons) {
        const boundary = closeRing(cellToBoundary(cell.h3Index, true))
        return {
          type: 'Feature',
          properties: { ...cell },
          geometry: {
            type: 'Polygon',
            coordinates: [boundary],
          } as Polygon,
        }
      }

      const [lat, lng] = cellToLatLng(cell.h3Index)
      return {
        type: 'Feature',
        properties: { ...cell },
        geometry: {
          type: 'Point',
          coordinates: [lng, lat],
        } as Point,
      }
    })

    return {
      type: 'FeatureCollection',
      features,
    } as FeatureCollection
  }, [cells, usePolygons])
}
