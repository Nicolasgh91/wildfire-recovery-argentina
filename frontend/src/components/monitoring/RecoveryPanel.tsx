import { AlertTriangle, Leaf } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { NdviChart } from '@/components/ndvi-chart'
import { RecoveryStatusBadge } from './RecoveryStatusBadge'
import { LandUseChangeCard } from './LandUseChangeCard'
import { useRecovery } from '@/hooks/queries/useRecovery'
import { useRecoveryByEpisode } from '@/hooks/queries/useRecoveryByEpisode'
import { useLandUseChanges } from '@/hooks/queries/useLandUseChanges'
import type { MonthlyNDVI } from '@/services/endpoints/monitoring'

interface RecoveryPanelProps {
  /** ID del evento (vista evento). Obligatorio si no se pasa episodeId. */
  fireEventId: string
  /** ID del episodio (vista episodio, Fase 6). Si se pasa, se usa recovery agregado por episodio. */
  episodeId?: string
  /** Fecha del incendio del detalle del evento (p. ej. fire.start_date). Si no se pasa, se usa recovery.fire_date. */
  fireDate?: string
}

export function RecoveryPanel({
  fireEventId,
  episodeId,
  fireDate: fireDateFromDetail,
}: RecoveryPanelProps) {
  const byEvent = useRecovery(fireEventId, !episodeId)
  const byEpisode = useRecoveryByEpisode(episodeId ?? '', !!episodeId)
  const recoveryResult = episodeId ? byEpisode : byEvent
  const { data: recovery, isLoading: recoveryLoading, error: recoveryError } = recoveryResult
  const { data: landUse, isLoading: landUseLoading } = useLandUseChanges(
    fireEventId,
    !episodeId,
  )

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
          {recovery.message ||
            'El monitoreo de vegetacion se ejecuta mensualmente. Los datos estaran disponibles una vez que se procese el primer analisis NDVI.'}
        </p>
      </div>
    )
  }

  const baselineNdvi = recovery.baseline_ndvi ?? 0.5
  const fireDate = fireDateFromDetail ?? recovery.fire_date
  const monitoringData: MonthlyNDVI[] = recovery.monitoring_data

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

      {monitoringData.length > 0 ? (
        <NdviChart
          data={monitoringData}
          baselineNdvi={baselineNdvi}
          fireDate={fireDate}
        />
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
