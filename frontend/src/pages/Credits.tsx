import { useState } from 'react'
import { Coins } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PaymentButton } from '@/components/payments/PaymentButton'
import { useCreditBalance } from '@/hooks/queries/useCreditBalance'
import { useI18n } from '@/context/LanguageContext'

export default function CreditsPage() {
  const { t } = useI18n()
  const { data, isLoading } = useCreditBalance()
  const [creditsAmount, setCreditsAmount] = useState('5')
  const parsedCredits = Number.parseInt(creditsAmount, 10)
  const isValidCredits =
    Number.isFinite(parsedCredits) && parsedCredits >= 1 && parsedCredits <= 100

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Coins className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('creditsTitle')}</h1>
          <p className="text-muted-foreground">{t('creditsDescription')}</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{t('creditsBalance')}</CardTitle>
            <CardDescription>{t('creditsBalanceHint')}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-foreground">
              {isLoading ? t('loading') : data?.balance ?? 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('creditsPurchaseTitle')}</CardTitle>
            <CardDescription>{t('creditsPurchaseDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="credits-amount">{t('creditsAmountLabel')}</Label>
              <Input
                id="credits-amount"
                type="number"
                min={1}
                max={100}
                step={1}
                inputMode="numeric"
                value={creditsAmount}
                onChange={(event) => setCreditsAmount(event.target.value)}
                placeholder={t('creditsAmountPlaceholder')}
              />
              <p className="text-xs text-muted-foreground">{t('creditsAmountHint')}</p>
              {!isValidCredits && (
                <p className="text-xs text-destructive">{t('creditsAmountError')}</p>
              )}
            </div>
            <PaymentButton
              purpose="credits"
              creditsAmount={isValidCredits ? parsedCredits : undefined}
              disabled={!isValidCredits}
              className="w-full"
            >
              {t('creditsProceed')}
            </PaymentButton>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
