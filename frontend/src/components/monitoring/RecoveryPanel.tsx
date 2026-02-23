import { AlertTriangle, Leaf, ShieldAlert } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { NdviChart } from '@/components/ndvi-chart'
import { RecoveryStatusBadge } from './RecoveryStatusBadge'
import { useRecovery } from '@/hooks/queries/useRecovery'
import { useLandUseChanges } from '@/hooks/queries/useLandUseChanges'
import type { LandUseChangeItem } from '@/services/endpoints/monitoring'

interface RecoveryPanelProps {
  fireEventId: string
}

function LandUseChangeCard({ change }: { change: LandUseChangeItem }) {
  const severityColors: Record<string, string> = {
    critical: 'border-red-200 bg-red-50 text-red-800',
    high: 'border-orange-200 bg-orange-50 text-orange-800',
    medium: 'border-amber-200 bg-amber-50 text-amber-800',
    low: 'border-muted bg-muted/40 text-muted-foreground',
  }

  return (
    <div className="rounded-lg border border-border p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{change.change_type}</span>
        <div className="flex gap-2">
          {change.change_severity && (
            <Badge variant="outline" className={severityColors[change.change_severity] ?? severityColors.low}>
              {change.change_severity}
            </Badge>
          )}
          {change.is_potential_violation && (
            <Badge variant="destructive" className="gap-1">
              <ShieldAlert className="h-3 w-3" />
              Violacion
            </Badge>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>Detectado: {new Date(change.change_detected_at).toLocaleDateString()}</span>
        {change.months_after_fire != null && <span>{change.months_after_fire} meses post-incendio</span>}
        {change.affected_area_hectares != null && <span>{change.affected_area_hectares.toFixed(1)} ha</span>}
      </div>
      {change.notes && <p className="text-xs text-muted-foreground">{change.notes}</p>}
    </div>
  )
}

export function RecoveryPanel({ fireEventId }: RecoveryPanelProps) {
  const { data: recovery, isLoading: recoveryLoading, error: recoveryError } = useRecovery(fireEventId)
  const { data: landUse, isLoading: landUseLoading } = useLandUseChanges(fireEventId)

  if (recoveryLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[300px] w-full" />
        <Skeleton className="h-24 w-full" />
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
