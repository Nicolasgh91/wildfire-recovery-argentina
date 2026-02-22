import { GeoJSON } from 'react-leaflet'
import type { Feature, FeatureCollection } from 'geojson'
import type { Layer, LeafletMouseEvent, Path } from 'leaflet'
import { useMemo } from 'react'
import { useI18n } from '@/context/LanguageContext'
import { PROTECTED_AREA_HOVER_STYLE, PROTECTED_AREA_STYLE } from '@/lib/leaflet/styles'

export type ProtectedAreaProperties = {
  id?: string
  name?: string
  category?: string
  [key: string]: unknown
}

interface ProtectedAreasProps {
  data?: FeatureCollection | null
  visible?: boolean
  onAreaClick?: (properties: ProtectedAreaProperties) => void
}

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;')

const buildPopupHtml = (props: ProtectedAreaProperties, fallbackLabel: string) => {
  const name = escapeHtml(props.name ?? fallbackLabel)
  const category = props.category ? escapeHtml(props.category) : null

  return `
    <div style="min-width:200px;padding:8px;">
      <div style="font-weight:600;margin-bottom:4px;">${name}</div>
      ${category ? `<div style="font-size:12px;color:#475569;">${category}</div>` : ''}
    </div>
  `
}

export function ProtectedAreas({ data, visible = true, onAreaClick }: ProtectedAreasProps) {
  const { t } = useI18n()
  const features = useMemo(() => data?.features ?? [], [data])

  if (!visible || features.length === 0) return null

  const fallbackLabel = escapeHtml(t('protectedArea'))

  const onEachFeature = (feature: Feature, layer: Layer) => {
    const props = (feature.properties ?? {}) as ProtectedAreaProperties
    layer.bindPopup(buildPopupHtml(props, fallbackLabel))

    layer.on({
      click: () => onAreaClick?.(props),
      mouseover: (e: LeafletMouseEvent) => {
        const target = e.target as Path
        target.setStyle(PROTECTED_AREA_HOVER_STYLE)
      },
      mouseout: (e: LeafletMouseEvent) => {
        const target = e.target as Path
        target.setStyle(PROTECTED_AREA_STYLE)
      },
    })
  }

  const style = () => PROTECTED_AREA_STYLE

  return <GeoJSON data={data as FeatureCollection} style={style} onEachFeature={onEachFeature} />
}
