import type { ReactNode } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts'
import { Cloud } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'
import type { MonthlyNDVI } from '@/services/endpoints/monitoring'

/** Serie interna para Recharts: transformación desde MonthlyNDVI[] dentro del componente. */
interface ChartSeriesPoint {
  date: string
  ndvi: number
  recovery: number | undefined
  cloudCover: number | undefined
}

export interface NdviChartProps {
  data: MonthlyNDVI[]
  /** Baseline NDVI; line is hidden when null. */
  baselineNdvi: number | null
  fireDate: string
  /** Show reference line for fire date and baseline. Default true. */
  showAnnotations?: boolean
}

/** Zonas NDVI: &lt; 0.2 rojo, 0.2–0.4 naranja, 0.4–0.6 verde claro, &gt; 0.6 verde */
const NDVI_ZONES = [
  { y1: 0, y2: 0.2, fill: 'hsl(0 84% 60%)', fillOpacity: 0.25 },
  { y1: 0.2, y2: 0.4, fill: 'hsl(25 95% 53%)', fillOpacity: 0.25 },
  { y1: 0.4, y2: 0.6, fill: 'hsl(142 76% 76%)', fillOpacity: 0.25 },
  { y1: 0.6, y2: 1, fill: 'hsl(142 71% 45%)', fillOpacity: 0.25 },
] as const

interface NdviTooltipContentProps {
  active?: boolean
  payload?: Array<{ payload: ChartSeriesPoint }>
  label?: ReactNode
}

function NdviTooltipContent({ active, payload, label }: NdviTooltipContentProps) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  if (!point) return null
  const labelStr =
    typeof label === 'string'
      ? label
      : label != null
        ? String(label)
        : point.date
  const d = new Date(labelStr)
  const dateLabel = Number.isNaN(d.getTime()) ? labelStr : d.toLocaleDateString('es-AR')
  const cloudPct = point.cloudCover ?? 0
  const showCloud = cloudPct > 30

  return (
    <div
      className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground shadow-sm"
      style={{
        backgroundColor: 'hsl(var(--card))',
        borderColor: 'hsl(var(--border))',
        color: 'hsl(var(--foreground))',
      }}
    >
      <p className="font-medium">{dateLabel}</p>
      <p>NDVI: {point.ndvi.toFixed(3)}</p>
      {point.recovery != null && (
        <p>Nivel de vegetación: {point.recovery.toFixed(1)}%</p>
      )}
      {(point.cloudCover != null || showCloud) && (
        <p className="flex items-center gap-1.5">
          {showCloud && <Cloud className="h-4 w-4" aria-hidden />}
          Nubes: {point.cloudCover != null ? `${point.cloudCover.toFixed(0)}%` : '—'}
        </p>
      )}
    </div>
  )
}

export function NdviChart({
  data,
  baselineNdvi,
  fireDate,
  showAnnotations = true,
}: NdviChartProps) {
  const { t } = useI18n()

  const chartSeries: ChartSeriesPoint[] = data.map((d) => ({
    date: d.date,
    ndvi: d.ndvi_mean,
    recovery: d.recovery_percentage ?? undefined,
    cloudCover: d.cloud_cover_pct ?? undefined,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {t('vegetationRecovery')}
        </CardTitle>
        <CardDescription>
          NDVI values range from 0 (no vegetation) to 1 (dense vegetation)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartSeries}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              {NDVI_ZONES.map((zone, i) => (
                <ReferenceArea
                  key={i}
                  y1={zone.y1}
                  y2={zone.y2}
                  fill={zone.fill}
                  fillOpacity={zone.fillOpacity}
                />
              ))}
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tick={{ fill: 'currentColor' }}
                tickFormatter={(v: string) => {
                  const d = new Date(v)
                  return Number.isNaN(d.getTime())
                    ? v
                    : d.toLocaleDateString('es-AR', { month: 'short', year: '2-digit' })
                }}
              />
              <YAxis
                domain={[0, 1]}
                className="text-xs"
                tick={{ fill: 'currentColor' }}
                tickFormatter={(value: number) => value.toFixed(1)}
              />
              <Tooltip
                content={<NdviTooltipContent />}
                labelFormatter={(label: ReactNode) => {
                  const str =
                    label == null
                      ? ''
                      : typeof label === 'string'
                        ? label
                        : typeof label === 'number'
                          ? String(label)
                          : String(label)
                  const d = new Date(str)
                  return Number.isNaN(d.getTime()) ? str : d.toLocaleDateString('es-AR')
                }}
              />
              {showAnnotations && (
                <ReferenceLine
                  x={fireDate}
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  label={{ value: 'Incendio', fill: 'hsl(var(--destructive))', fontSize: 11 }}
                />
              )}
              {showAnnotations && baselineNdvi != null && (
                <ReferenceLine
                  y={baselineNdvi}
                  stroke="hsl(var(--primary))"
                  strokeDasharray="5 5"
                  label={{
                    value: `Baseline (${baselineNdvi.toFixed(2)})`,
                    fill: 'hsl(var(--primary))',
                    fontSize: 12,
                  }}
                />
              )}
              <Line
                type="monotone"
                dataKey="ndvi"
                stroke="hsl(var(--chart-1))"
                strokeWidth={3}
                dot={{ fill: 'hsl(var(--chart-1))', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, fill: 'hsl(var(--primary))' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
