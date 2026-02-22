import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'
import type { UserCredits } from '@/types/credits'

interface CreditBalanceProps {
  credits?: UserCredits | null
  requiredCredits: number
}

export function CreditBalance({ credits, requiredCredits }: CreditBalanceProps) {
  const { t } = useI18n()
  const balance = credits?.balance ?? 0
  const isFallback = credits?.source === 'fallback'
  const isEnough = balance >= requiredCredits

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{t('reportCreditsAvailable')}</p>
          <p className="text-2xl font-semibold text-foreground">{balance}</p>
          {isFallback && (
            <p className="text-xs text-muted-foreground">{t('creditsFallback')}</p>
          )}
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <p className="text-sm text-muted-foreground">{t('reportCreditsRequired')}</p>
          <Badge variant={isEnough ? 'secondary' : 'destructive'}>
            {requiredCredits}
          </Badge>
          <p className="text-xs text-muted-foreground">{t('reportCreditsHint')}</p>
        </div>
      </CardContent>
    </Card>
  )
}
