import { useMemo, useState } from 'react'
import { User as UserIcon, Wallet } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PaymentButton } from '@/components/payments/PaymentButton'
import { useAuth } from '@/context/AuthContext'
import { useI18n } from '@/context/LanguageContext'
import { useUserCredits } from '@/hooks/queries/useUserCredits'

export default function ProfilePage() {
  const { t } = useI18n()
  const { user } = useAuth()
  const { data: credits } = useUserCredits()

  const initialName = useMemo(() => {
    const metadata = user?.user_metadata ?? {}
    return (metadata.full_name as string) || (metadata.name as string) || ''
  }, [user])

  const [fullName, setFullName] = useState(initialName)
  const [isSaving, setIsSaving] = useState(false)
  const [creditsAmount, setCreditsAmount] = useState('5')
  const parsedCredits = Number.parseInt(creditsAmount, 10)
  const isValidCredits =
    Number.isFinite(parsedCredits) && parsedCredits >= 1 && parsedCredits <= 100

  const handleSave = async () => {
    setIsSaving(true)
    const { error } = await supabase.auth.updateUser({
      data: { full_name: fullName.trim() },
    })

    if (error) {
      toast.error(t('profileSaveError'))
    } else {
      toast.success(t('profileSaveSuccess'))
    }

    setIsSaving(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <UserIcon className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('profileTitle')}</h1>
          <p className="text-muted-foreground">{t('profileDescription')}</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{t('profileEditTitle')}</CardTitle>
            <CardDescription>{t('profileEditDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="profile-name">{t('profileNameLabel')}</Label>
              <Input
                id="profile-name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder={t('profileNamePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="profile-email">{t('profileEmailLabel')}</Label>
              <Input id="profile-email" value={user?.email ?? ''} readOnly />
            </div>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? t('loading') : t('profileSave')}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-primary" />
              {t('profileCreditsTitle')}
            </CardTitle>
            <CardDescription>{t('profileCreditsDescription')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-4 py-3">
              <span className="text-sm text-muted-foreground">{t('creditsBalance')}</span>
              <span className="text-lg font-semibold text-foreground">
                {credits?.balance ?? 0}
              </span>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-credits-amount">{t('creditsAmountLabel')}</Label>
              <Input
                id="profile-credits-amount"
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
