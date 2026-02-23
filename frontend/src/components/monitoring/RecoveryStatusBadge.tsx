import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type RecoveryStatus =
  | 'not_started'
  | 'early_recovery'
  | 'moderate_recovery'
  | 'advanced_recovery'
  | 'full_recovery'
  | 'stalled'
  | 'anomaly_detected'
  | 'pending'

interface RecoveryStatusBadgeProps {
  status: string | null | undefined
  className?: string
}

const statusConfig: Record<RecoveryStatus, { label: string; className: string }> = {
  not_started: { label: 'Sin monitoreo', className: 'bg-muted text-muted-foreground border-muted' },
  pending: { label: 'Pendiente', className: 'bg-muted text-muted-foreground border-muted' },
  early_recovery: { label: 'En recuperacion', className: 'border-amber-200 bg-amber-100 text-amber-800' },
  moderate_recovery: { label: 'En recuperacion', className: 'border-amber-200 bg-amber-100 text-amber-800' },
  advanced_recovery: { label: 'Recuperado', className: 'border-emerald-200 bg-emerald-100 text-emerald-700' },
  full_recovery: { label: 'Recuperado', className: 'border-emerald-200 bg-emerald-100 text-emerald-700' },
  stalled: { label: 'Estancado', className: 'border-orange-200 bg-orange-100 text-orange-800' },
  anomaly_detected: { label: 'Alerta', className: 'border-red-200 bg-red-100 text-red-700' },
}

export function RecoveryStatusBadge({ status, className }: RecoveryStatusBadgeProps) {
  if (!status) return null

  const config = statusConfig[status as RecoveryStatus] ?? statusConfig.not_started

  return (
    <Badge variant="outline" className={cn(config.className, className)}>
      {config.label}
    </Badge>
  )
}
