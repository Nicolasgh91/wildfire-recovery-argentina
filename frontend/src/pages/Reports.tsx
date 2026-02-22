import { useState } from 'react'
import { FileCheck2 } from 'lucide-react'
import { useI18n } from '@/context/LanguageContext'
import { useUserCredits } from '@/hooks/queries/useUserCredits'
import { CreditBalance } from '@/components/reports/CreditBalance'
import { ReportRequestForm } from '@/components/reports/ReportRequestForm'
import { ReportStatus } from '@/components/reports/ReportStatus'
import { DEFAULT_REPORT_IMAGES } from '@/lib/reports'
import type { PendingReportApproval, ReportOutcome } from '@/types/report-ui'

export default function ReportsPage() {
  const { t } = useI18n()
  const { data: credits } = useUserCredits()
  const [estimatedCredits, setEstimatedCredits] = useState(DEFAULT_REPORT_IMAGES)
  const [pendingApproval, setPendingApproval] = useState<PendingReportApproval | null>(null)
  const [reportOutcome, setReportOutcome] = useState<ReportOutcome | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleResetStatus = () => {
    setPendingApproval(null)
    setReportOutcome(null)
    setErrorMessage(null)
  }

  return (
    <div className="bg-background">
      <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <FileCheck2 className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('reportsTitle')}</h1>
          <p className="text-muted-foreground">{t('reportsDescription')}</p>
        </div>

        <CreditBalance credits={credits} requiredCredits={estimatedCredits} />

        <ReportRequestForm
          creditsBalance={credits?.balance ?? null}
          onCostChange={setEstimatedCredits}
          onPendingApproval={setPendingApproval}
          onReportCreated={setReportOutcome}
          onError={setErrorMessage}
          onResetStatus={handleResetStatus}
        />

        <ReportStatus
          pendingApproval={pendingApproval}
          reportOutcome={reportOutcome}
          errorMessage={errorMessage}
        />
      </div>
    </div>
  )
}
