import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'
import { cn } from '@/lib/utils'

interface ReliabilityScoreProps {
  score: number
}

export function ReliabilityScore({ score }: ReliabilityScoreProps) {
  const { t } = useI18n()

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-primary'
    if (score >= 60) return 'text-accent'
    return 'text-destructive'
  }

  const getProgressColor = (score: number) => {
    if (score >= 80) return '[&>div]:bg-primary'
    if (score >= 60) return '[&>div]:bg-accent'
    return '[&>div]:bg-destructive'
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t('reliabilityScore')}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Progress 
              value={score} 
              className={cn('h-3', getProgressColor(score))}
            />
          </div>
          <span className={cn('text-2xl font-bold', getScoreColor(score))}>
            {score}%
          </span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Based on satellite imagery analysis and cross-validation
        </p>
      </CardContent>
    </Card>
  )
}
