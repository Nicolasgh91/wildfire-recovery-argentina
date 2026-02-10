import { GeoJSON } from 'react-leaflet'
import type { Layer, LeafletMouseEvent, Path } from 'leaflet'
import type { Feature } from 'geojson'
import { useMemo } from 'react'
import { useI18n } from '@/context/LanguageContext'
import { useH3Conversion } from '../hooks/useH3Conversion'
import { getEpisodeStyle, type MapSeverity, type MapStatus } from '@/lib/leaflet/styles'

export type Episode = {
  id: string
  title?: string
  h3_index: string
  severity?: MapSeverity
  status?: MapStatus
  province?: string | null
  hectares?: number | null
  in_protected_area?: boolean
  overlap_percentage?: number | null
  protected_area_name?: string | null
  count_protected_areas?: number | null
}

interface EpisodeLayerProps {
  episodes: Episode[]
  onEpisodeClick?: (episode: Episode) => void
}

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;')

function formatHectares(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  return value.toLocaleString('es-AR')
}

export function EpisodeLayer({ episodes, onEpisodeClick }: EpisodeLayerProps) {
  const { t } = useI18n()

  const cells = useMemo(
    () =>
      episodes
        .filter((episode) => Boolean(episode.h3_index))
        .map((episode) => ({
          h3Index: episode.h3_index,
          ...episode,
        })),
    [episodes]
  )

  const geojson = useH3Conversion(cells, { asPolygons: true })

  const buildPopupHtml = (episode: Episode) => {
    const title = escapeHtml(episode.title ?? `Incendio ${episode.id}`)
    const areaLabel = escapeHtml(t('area'))
    const provinceLabel = escapeHtml(t('province'))
    const detailsLabel = escapeHtml(t('viewDetails'))
    const protectedLabel = escapeHtml(t('protectedArea'))
    const hectares = escapeHtml(formatHectares(episode.hectares))
    const province = escapeHtml(episode.province ?? 'N/A')
    const detailsHref = `/fires/${encodeURIComponent(episode.id)}`

    const protectedLine =
      episode.in_protected_area && episode.overlap_percentage !== null && episode.overlap_percentage !== undefined
        ? `<div>${protectedLabel}: ${episode.overlap_percentage.toFixed(1)}%</div>`
        : episode.in_protected_area
          ? `<div>${protectedLabel}</div>`
          : ''

    const protectedName =
      episode.in_protected_area && episode.protected_area_name
        ? `<div>${protectedLabel}: ${escapeHtml(episode.protected_area_name)}</div>`
        : ''

    const protectedCount =
      episode.in_protected_area &&
      episode.count_protected_areas !== null &&
      episode.count_protected_areas !== undefined
        ? `<div>${protectedLabel}: ${episode.count_protected_areas}</div>`
        : ''

    return `
      <div style="min-width:200px;padding:8px;">
        <div style="font-weight:600;margin-bottom:6px;">${title}</div>
        <div style="font-size:12px;color:#475569;margin-bottom:8px;">
          <div>${areaLabel}: ${hectares} ha</div>
          <div>${provinceLabel}: ${province}</div>
          ${protectedLine}
          ${protectedName}
          ${protectedCount}
        </div>
        <a href="${detailsHref}" style="display:block;text-align:center;background:#10b981;color:white;padding:6px 8px;border-radius:6px;text-decoration:none;font-size:12px;">
          ${detailsLabel}
        </a>
      </div>
    `
  }

  const onEachFeature = (feature: Feature, layer: Layer) => {
    const episode = feature.properties as Episode
    if (!episode) return

    layer.bindPopup(buildPopupHtml(episode))

    layer.on({
      click: () => onEpisodeClick?.(episode),
      mouseover: (e: LeafletMouseEvent) => {
        const target = e.target as Path
        target.setStyle({
          weight: 3,
          fillOpacity: 0.8,
        })
      },
      mouseout: (e: LeafletMouseEvent) => {
        const target = e.target as Path
        target.setStyle(getEpisodeStyle(episode))
      },
    })
  }

  const style = (feature: Feature | undefined) => {
    if (!feature?.properties) return {}
    return getEpisodeStyle(feature.properties as Episode)
  }

  if (!episodes.length) return null

  return <GeoJSON data={geojson} style={style} onEachFeature={onEachFeature} />
}
