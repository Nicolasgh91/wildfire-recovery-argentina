import { Link } from 'react-router-dom'
import { AlertTriangle, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'

export default function NotFoundPage() {
  const { t } = useI18n()

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto flex max-w-xl items-center justify-center px-4 py-20">
        <Card className="w-full border-border bg-card">
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="h-7 w-7 text-destructive" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{t('notFoundTitle')}</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('notFoundMessage')}
              </p>
            </div>
            <Button asChild className="gap-2">
              <Link to="/">
                <Home className="h-4 w-4" />
                {t('notFoundBackHome')}
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
