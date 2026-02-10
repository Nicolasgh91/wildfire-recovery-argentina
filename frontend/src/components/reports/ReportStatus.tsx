import { AlertTriangle, CheckCircle2, Clock, FileText } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'
import type { PendingReportApproval, ReportOutcome } from '@/types/report-ui'

interface ReportStatusProps {
  pendingApproval?: PendingReportApproval | null
  reportOutcome?: ReportOutcome | null
  errorMessage?: string | null
}

const formatDate = (value: string | null | undefined, locale: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale).format(date)
}

export function ReportStatus({
  pendingApproval,
  reportOutcome,
  errorMessage,
}: ReportStatusProps) {
  const { t, language } = useI18n()
  const locale = language === 'es' ? 'es-AR' : 'en-US'

  if (errorMessage) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-5 w-5" />
        <AlertTitle>{t('reportError')}</AlertTitle>
        <AlertDescription>{errorMessage}</AlertDescription>
      </Alert>
    )
  }

  if (pendingApproval) {
    return (
      <Alert className="border-amber-500/40 bg-amber-500/10">
        <Clock className="h-5 w-5 text-amber-600" />
        <AlertTitle>{t('reportPendingApproval')}</AlertTitle>
        <AlertDescription className="mt-2 space-y-2 text-sm text-muted-foreground">
          <p>{pendingApproval.summary}</p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">
              {pendingApproval.reportType === 'judicial'
                ? t('judicialReport')
                : t('historicalReport')}
            </Badge>
            <Badge variant="secondary">
              {t('reportCreditsRequired')}: {pendingApproval.requiredCredits}
            </Badge>
            <Badge variant="outline">
              {formatDate(pendingApproval.requestedAt, locale)}
            </Badge>
          </div>
          <p>{t('reportPendingApprovalMessage')}</p>
        </AlertDescription>
      </Alert>
    )
  }

  if (!reportOutcome) return null

  const metadata = reportOutcome.response.report
  const isHistorical = metadata.report_type === 'historical'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          {t('reportSubmitted')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Alert className="border-primary/40 bg-primary/5">
          <CheckCircle2 className="h-5 w-5 text-primary" />
          <AlertTitle>{t('reportReady')}</AlertTitle>
          <AlertDescription className="mt-2 text-sm text-muted-foreground">
            {t('reportReadyMessage')}
          </AlertDescription>
        </Alert>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground">{t('reportId')}</p>
            <p className="text-lg font-semibold text-foreground">{metadata.report_id}</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground">{t('reportType')}</p>
            <p className="text-lg font-semibold text-foreground">
              {isHistorical ? t('historicalReport') : t('judicialReport')}
            </p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground">{t('reportGeneratedAt')}</p>
            <p className="text-lg font-semibold text-foreground">
              {formatDate(metadata.generated_at, locale)}
            </p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground">{t('reportCreditsRequired')}</p>
            <p className="text-lg font-semibold text-foreground">
              {reportOutcome.requiredCredits}
            </p>
          </div>
        </div>

        {isHistorical && 'fires_included' in reportOutcome.response && (
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground">{t('reportFiresIncluded')}</p>
            <p className="text-lg font-semibold text-foreground">
              {reportOutcome.response.fires_included}
            </p>
          </div>
        )}

        <div className="rounded-lg border border-border p-4">
          <p className="text-sm text-muted-foreground">{t('reportVerificationHash')}</p>
          <p className="break-all text-sm text-foreground">{metadata.verification_hash}</p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <a
            href={metadata.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {t('reportDownload')}
          </a>
          <a
            href={metadata.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            {t('reportOpenViewer')}
          </a>
        </div>
      </CardContent>
    </Card>
  )
}
