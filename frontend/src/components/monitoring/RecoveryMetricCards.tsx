interface RecoveryMetricCardsProps {
  baselineNdvi: number | null
  currentNdvi: number | null
  recoveryPercentage: number | null
  monthsMonitored: number
}

function MetricCard({
  label,
  value,
  sublabel,
}: {
  label: string
  value: string
  sublabel: string
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground">{sublabel}</p>
    </div>
  )
}

export function RecoveryMetricCards({
  baselineNdvi,
  currentNdvi,
  recoveryPercentage,
  monthsMonitored,
}: RecoveryMetricCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <MetricCard
        label="NDVI baseline"
        value={baselineNdvi?.toFixed(3) ?? '—'}
        sublabel="Pre-incendio"
      />
      <MetricCard
        label="NDVI actual"
        value={currentNdvi?.toFixed(3) ?? '—'}
        sublabel="Último análisis"
      />
      <MetricCard
        label="Nivel de vegetación"
        value={
          recoveryPercentage != null
            ? `${recoveryPercentage.toFixed(1)}%`
            : '—'
        }
        sublabel="% del baseline"
      />
      <MetricCard
        label="Meses monitoreados"
        value={monthsMonitored.toString()}
        sublabel="Desde el incendio"
      />
    </div>
  )
}
