import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { getRecoverySummary, type RecoverySummaryResponse } from '@/services/endpoints/monitoring'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LegalDisclaimer } from '@/components/monitoring/LegalDisclaimer'
import { RecoveryStatusBadge } from '@/components/monitoring/RecoveryStatusBadge'

function SummaryCard({
  label,
  value,
  sublabel,
}: {
  label: string
  value: string | number
  sublabel?: string
}) {
  return (
    <Card className="border-muted">
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-2xl font-semibold tracking-tight">{value}</p>
        {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
      </CardContent>
    </Card>
  )
}

function StatusBreakdown({ summary }: { summary: RecoverySummaryResponse }) {
  const entries = Object.entries(summary.status_breakdown ?? {})

  if (!entries.length) return null

  const total = entries.reduce((acc, [, v]) => acc + (v ?? 0), 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Distribución por estado de recuperación</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([status, count]) => {
          const value = count ?? 0
          const pct = total > 0 ? (value / total) * 100 : 0
          return (
            <div key={status} className="flex items-center gap-3">
              <div className="w-40 shrink-0">
                <RecoveryStatusBadge status={status} />
              </div>
              <div className="flex-1">
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary transition-[width]"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <div className="w-20 text-right text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{value}</span>
                {total > 0 && <span className="ml-1">({pct.toFixed(0)}%)</span>}
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

export default function MonitoringDashboard() {
  const { t } = useI18n()
  const { isAuthenticated } = useAuth()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['recovery-summary'],
    queryFn: ({ signal }) => getRecoverySummary(signal),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-6 md:py-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Monitoreo de recuperación de vegetación
        </h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Panorama agregado del estado de recuperación de los incendios monitoreados mediante NDVI.
          Los valores representan el nivel de vegetación respecto del baseline pre-incendio.
        </p>
      </header>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="h-4 w-4 animate-spin rounded-full border border-muted border-t-transparent" />
          <span>{t('loading') ?? 'Cargando datos de monitoreo...'}</span>
        </div>
      )}

      {isError && !isLoading && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>No se pudieron cargar los datos de monitoreo. Intenta nuevamente más tarde.</span>
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <section className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            <SummaryCard label="Eventos monitoreados" value={data.total_monitored_events} />
            <SummaryCard
              label="Recuperación promedio"
              value={`${data.average_recovery_percentage?.toFixed(1) ?? '–'}%`}
              sublabel="% del NDVI pre-incendio"
            />
            <Card className="border-muted">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-medium text-muted-foreground">
                  Acceso
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <Badge variant="outline" className="text-xs">
                  {isAuthenticated ? 'Usuario autenticado' : 'Acceso público'}
                </Badge>
                <p className="mt-2 text-xs text-muted-foreground">
                  Este resumen es público; el detalle por evento y datos de violaciones solo están
                  disponibles para usuarios autenticados.
                </p>
              </CardContent>
            </Card>
          </section>

          <section className="space-y-3">
            <StatusBreakdown summary={data} />
          </section>

          <section>
            <LegalDisclaimer text={data.legal_disclaimer} />
          </section>
        </>
      )}
    </div>
  )
}

