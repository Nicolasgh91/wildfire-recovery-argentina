import { describe, expect, it } from 'vitest'
import { renderHook } from '@testing-library/react'
import { cellToLatLng, latLngToCell } from 'h3-js'
import { useH3Conversion } from '../useH3Conversion'

describe('useH3Conversion', () => {
  const h3Index = latLngToCell(-34.6037, -58.3816, 5)

  it('converts empty array to empty FeatureCollection', () => {
    const { result } = renderHook(() => useH3Conversion([]))
    expect(result.current.type).toBe('FeatureCollection')
    expect(result.current.features).toHaveLength(0)
  })

  it('converts H3 index to polygon', () => {
    const { result } = renderHook(() => useH3Conversion([{ h3Index }], { asPolygons: true }))
    const feature = result.current.features[0]
    expect(feature.geometry.type).toBe('Polygon')

    const ring = (feature.geometry as GeoJSON.Polygon).coordinates[0]
    expect(ring.length).toBeGreaterThan(3)
    expect(ring[0]).toEqual(ring[ring.length - 1])
  })

  it('converts H3 index to centroid point', () => {
    const { result } = renderHook(() => useH3Conversion([{ h3Index }], { asPolygons: false }))
    const feature = result.current.features[0]
    expect(feature.geometry.type).toBe('Point')

    const [lat, lng] = cellToLatLng(h3Index)
    expect((feature.geometry as GeoJSON.Point).coordinates).toEqual([lng, lat])
  })

  it('preserves properties in features', () => {
    const { result } = renderHook(() =>
      useH3Conversion([{ h3Index, intensity: 0.5, source: 'test' }], { asPolygons: true })
    )
    const props = result.current.features[0].properties as Record<string, unknown>
    expect(props.intensity).toBe(0.5)
    expect(props.source).toBe('test')
  })

  it('memoizes result correctly', () => {
    const cells = [{ h3Index, intensity: 0.2 }]
    const { result, rerender } = renderHook(
      ({ asPolygons }) => useH3Conversion(cells, { asPolygons }),
      { initialProps: { asPolygons: true } }
    )

    const first = result.current
    rerender({ asPolygons: true })
    expect(result.current).toBe(first)
  })
})
