import { ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { LandUseChangeItem } from '@/services/endpoints/monitoring'

interface LandUseChangeCardProps {
  change: LandUseChangeItem
}

const severityColors: Record<string, string> = {
  critical: 'border-red-200 bg-red-50 text-red-800',
  high: 'border-orange-200 bg-orange-50 text-orange-800',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  low: 'border-muted bg-muted/40 text-muted-foreground',
}

export function LandUseChangeCard({ change }: LandUseChangeCardProps) {
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
        <span>Detectado: {new Date(change.change_detected_at).toLocaleDateString('es-AR')}</span>
        {change.months_after_fire != null && <span>{change.months_after_fire} meses post-incendio</span>}
        {change.affected_area_hectares != null && <span>{change.affected_area_hectares.toFixed(1)} ha</span>}
      </div>
      {change.notes && <p className="text-xs text-muted-foreground">{change.notes}</p>}
    </div>
  )
}
