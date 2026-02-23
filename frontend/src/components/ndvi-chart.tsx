import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'

interface NdviDataPoint {
  month: string
  value: number
  recovery_percentage?: number | null
  cloud_cover_pct?: number | null
}

interface NdviChartProps {
  data: NdviDataPoint[]
  baselineNdvi?: number | null
}

export function NdviChart({ data, baselineNdvi }: NdviChartProps) {
  const { t } = useI18n()

  const baseline = baselineNdvi ?? 0.5

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
              data={data}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="month"
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
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
                labelFormatter={(label: string) => {
                  const d = new Date(label)
                  return Number.isNaN(d.getTime()) ? label : d.toLocaleDateString('es-AR')
                }}
                formatter={(value: number, name: string) => {
                  if (name === 'value') return [value.toFixed(3), 'NDVI']
                  return [value, name]
                }}
              />
              <ReferenceLine
                y={baseline}
                stroke="hsl(var(--primary))"
                strokeDasharray="5 5"
                label={{
                  value: baselineNdvi != null ? `Baseline (${baseline.toFixed(2)})` : 'Healthy',
                  fill: 'hsl(var(--primary))',
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
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
