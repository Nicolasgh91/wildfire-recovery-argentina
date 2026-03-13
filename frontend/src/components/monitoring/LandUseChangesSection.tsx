import { Info } from 'lucide-react'
import { LegalDisclaimer } from './LegalDisclaimer'
import type { LandUseChangeItem, LandUseChangesResponse } from '@/services/endpoints/monitoring'

const CHANGE_TYPE_LABELS: Record<string, string> = {
  construction_detected: 'Posible construcción detectada',
  agriculture: 'Posible actividad agrícola',
  bare_soil: 'Suelo descubierto persistente',
  natural_recovery: 'Recuperación natural',
  uncertain: 'Cambio no clasificado',
}

const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Severidad alta',
  high: 'Severidad media-alta',
  medium: 'Severidad media',
  low: 'Severidad baja',
}

interface LandUseChangesSectionProps {
  changes: LandUseChangesResponse
}

function SectionChangeCard({ change }: { change: LandUseChangeItem }) {
  const dateFormatted = new Date(change.change_detected_at).toLocaleDateString(
    'es-AR',
    { year: 'numeric', month: 'short' },
  )

  return (
    <div className="rounded-lg border bg-card p-3 text-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium">
            {CHANGE_TYPE_LABELS[change.change_type] ?? change.change_type}
          </p>
          <p className="text-xs text-muted-foreground">
            {dateFormatted} — {change.months_after_fire ?? '—'} meses post-incendio
          </p>
        </div>
        {change.is_potential_violation && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <Info className="h-3.5 w-3.5" aria-hidden />
            Requiere verificación
          </span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {change.change_severity && (
          <span>{SEVERITY_LABELS[change.change_severity] ?? change.change_severity}</span>
        )}
        {change.affected_area_hectares != null && (
          <span>{change.affected_area_hectares.toFixed(1)} ha</span>
        )}
        {change.confidence_score != null && (
          <span>Confianza: {(change.confidence_score * 100).toFixed(0)}%</span>
        )}
        <span className="capitalize">
          {change.status === 'pending_review'
            ? 'Pendiente de verificación presencial'
            : change.status}
        </span>
      </div>
      {change.notes && (
        <p className="mt-1.5 text-xs italic text-muted-foreground">{change.notes}</p>
      )}
    </div>
  )
}

export function LandUseChangesSection({ changes }: LandUseChangesSectionProps) {
  if (!changes.changes.length) return null

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-muted-foreground">
        Cambios de uso de suelo detectados ({changes.total_changes})
      </h4>
      {changes.changes.map((change) => (
        <SectionChangeCard key={change.id} change={change} />
      ))}
      <LegalDisclaimer text={changes.legal_disclaimer} />
    </div>
  )
}
