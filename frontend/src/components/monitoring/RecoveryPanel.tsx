import { AlertTriangle, Leaf } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { NdviChart } from '@/components/ndvi-chart'
import { RecoveryStatusBadge } from './RecoveryStatusBadge'
import { LandUseChangeCard } from './LandUseChangeCard'
import { useRecovery } from '@/hooks/queries/useRecovery'
import { useLandUseChanges } from '@/hooks/queries/useLandUseChanges'

interface RecoveryPanelProps {
  fireEventId: string
}

export function RecoveryPanel({ fireEventId }: RecoveryPanelProps) {
  const { data: recovery, isLoading: recoveryLoading, error: recoveryError } = useRecovery(fireEventId)
  const { data: landUse, isLoading: landUseLoading } = useLandUseChanges(fireEventId)

  if (recoveryLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {/* Header skeleton */}
        <div className="flex items-center gap-3">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
        {/* Metric cards skeleton */}
        <div className="grid gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="mb-2 h-4 w-24" />
                <Skeleton className="h-7 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
        {/* Chart skeleton */}
        <Skeleton className="h-[300px] w-full rounded-xl" />
        {/* Land use cards skeleton */}
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (recoveryError) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        <AlertTriangle className="h-4 w-4" />
        No se pudieron cargar los datos de recuperacion.
      </div>
    )
  }

  if (!recovery) return null

  if (recovery.recovery_status === 'pending' && recovery.monitoring_data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
        <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mb-4">
          <Leaf className="w-8 h-8 text-emerald-400" />
        </div>
        <h3 className="text-sm font-medium text-foreground mb-1">
          Analisis de recuperacion pendiente
        </h3>
        <p className="text-xs text-muted-foreground max-w-xs">
          El monitoreo de vegetacion se ejecuta mensualmente. Los datos estaran disponibles
          una vez que se procese el primer analisis NDVI para este evento.
        </p>
      </div>
    )
  }

  const chartData = recovery.monitoring_data.map((d) => ({
    month: d.date,
    value: d.ndvi_mean,
    recovery_percentage: d.recovery_percentage,
    cloud_cover_pct: d.cloud_cover_pct,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Leaf className="h-5 w-5 text-emerald-600" />
        <h2 className="text-lg font-semibold text-foreground">Recuperacion Vegetal</h2>
        <RecoveryStatusBadge status={recovery.recovery_status} />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">NDVI Baseline</p>
            <p className="text-xl font-semibold text-foreground">
              {recovery.baseline_ndvi != null ? recovery.baseline_ndvi.toFixed(3) : 'Pendiente'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">NDVI Actual</p>
            <p className="text-xl font-semibold text-foreground">
              {recovery.current_ndvi != null ? recovery.current_ndvi.toFixed(3) : 'N/A'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Recuperacion</p>
            <p className="text-xl font-semibold text-foreground">
              {recovery.recovery_percentage != null ? `${recovery.recovery_percentage.toFixed(1)}%` : 'N/A'}
            </p>
          </CardContent>
        </Card>
      </div>

      {chartData.length > 0 ? (
        <NdviChart data={chartData} baselineNdvi={recovery.baseline_ndvi} />
      ) : (
        <Card>
          <CardContent className="flex items-center justify-center py-12 text-sm text-muted-foreground">
            No hay datos de monitoreo disponibles aun.
          </CardContent>
        </Card>
      )}

      {!landUseLoading && landUse && landUse.changes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Cambios de uso de suelo
              {landUse.violation_count > 0 && (
                <Badge variant="destructive">{landUse.violation_count} violacion(es)</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {landUse.changes.map((change) => (
              <LandUseChangeCard key={change.id} change={change} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
