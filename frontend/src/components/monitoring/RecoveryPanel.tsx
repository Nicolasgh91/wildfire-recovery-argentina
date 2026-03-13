import { AlertTriangle, Leaf } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { NdviChart } from '@/components/ndvi-chart'
import { RecoveryStatusBadge } from './RecoveryStatusBadge'
import { RecoveryMetricCards } from './RecoveryMetricCards'
import { LegalDisclaimer } from './LegalDisclaimer'
import { LandUseChangesSection } from './LandUseChangesSection'
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
  /** Si el usuario está autenticado: se fetchean land-use changes y se muestran anotaciones en el gráfico. */
  isAuthenticated?: boolean
}

function isCanceledError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const maybeAny = error as { code?: unknown }
  return maybeAny.code === 'ERR_CANCELED'
}

export function RecoveryPanel({
  fireEventId,
  episodeId,
  fireDate: fireDateFromDetail,
  isAuthenticated = false,
}: RecoveryPanelProps) {
  const byEvent = useRecovery(fireEventId, !episodeId)
  const byEpisode = useRecoveryByEpisode(episodeId ?? '', !!episodeId)
  const recoveryResult = episodeId ? byEpisode : byEvent
  const { data: recovery, isLoading: recoveryLoading, error: recoveryError } = recoveryResult
  const { data: landUse, isLoading: landUseLoading } = useLandUseChanges(
    isAuthenticated && !episodeId ? fireEventId : null,
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

  const canceled = isCanceledError(recoveryError)

  if (recoveryError && !canceled) {
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

  const fireDate = fireDateFromDetail ?? recovery.fire_date
  const monitoringData: MonthlyNDVI[] = recovery.monitoring_data

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Leaf className="h-5 w-5 text-emerald-600" />
        <h2 className="text-lg font-semibold text-foreground">Recuperacion Vegetal</h2>
        <RecoveryStatusBadge status={recovery.recovery_status} />
      </div>

      <RecoveryMetricCards
        baselineNdvi={recovery.baseline_ndvi}
        currentNdvi={recovery.current_ndvi}
        recoveryPercentage={recovery.recovery_percentage}
        monthsMonitored={recovery.months_monitored}
      />

      {monitoringData.length > 0 ? (
        <NdviChart
          data={monitoringData}
          baselineNdvi={recovery.baseline_ndvi ?? null}
          fireDate={fireDate}
          showAnnotations={isAuthenticated}
        />
      ) : (
        <Card>
          <CardContent className="flex items-center justify-center py-12 text-sm text-muted-foreground">
            No hay datos de monitoreo disponibles aun.
          </CardContent>
        </Card>
      )}

      {isAuthenticated && !landUseLoading && landUse && landUse.changes.length > 0 && (
        <LandUseChangesSection changes={landUse} />
      )}

      <LegalDisclaimer text={recovery.legal_disclaimer} />
    </div>
  )
}
