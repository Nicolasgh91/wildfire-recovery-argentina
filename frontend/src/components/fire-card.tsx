import { Link } from 'react-router-dom'
import { MapPin, Calendar, Flame, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/context/LanguageContext'
import type { Fire } from '@/data/mockdata'
import { cn } from '@/lib/utils'

interface FireCardProps {
  fire: Fire
}

export function FireCard({ fire }: FireCardProps) {
  const { t } = useI18n()
  const detailId = fire.id

  const severityColors = {
    high: 'bg-destructive text-destructive-foreground',
    medium: 'bg-accent text-accent-foreground',
    low: 'bg-primary/20 text-primary',
  }

  const severityLabels = {
    high: t('highSeverity'),
    medium: t('mediumSeverity'),
    low: t('lowSeverity'),
  }

  const statusColors = {
    active: 'bg-destructive/10 text-destructive border-destructive/30',
    extinguished: 'bg-muted text-muted-foreground border-muted',
  }

  return (
    <Card className="overflow-hidden transition-all hover:shadow-lg">
      {/* Map Thumbnail Placeholder */}
      <div className="relative aspect-video bg-gradient-to-br from-primary/20 via-primary/10 to-accent/20">
        <div className="absolute inset-0 flex items-center justify-center">
          <Flame className={cn(
            'h-16 w-16',
            fire.severity === 'high' ? 'text-destructive' : 
            fire.severity === 'medium' ? 'text-accent' : 'text-primary'
          )} />
        </div>
        <Badge className={cn('absolute top-3 left-3', severityColors[fire.severity])}>
          {severityLabels[fire.severity]}
        </Badge>
        <Badge 
          variant="outline" 
          className={cn('absolute top-3 right-3', statusColors[fire.status])}
        >
          {fire.status === 'active' ? t('active') : t('extinguished')}
        </Badge>
      </div>

      <CardContent className="p-4">
        <h3 className="mb-2 line-clamp-1 text-lg font-semibold text-foreground">
          {fire.title}
        </h3>
        
        <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="h-4 w-4" />
            {fire.province}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {new Date(fire.date).toLocaleDateString()}
          </span>
          <span className="flex items-center gap-1">
            <Flame className="h-4 w-4" />
            {fire.hectares.toLocaleString()} {t('hectares')}
          </span>
        </div>
      </CardContent>

      <CardFooter className="border-t border-border p-4">
        {detailId ? (
          <Button asChild variant="default" className="w-full gap-2">
            <Link to={`/fires/${detailId}`}>
              {t('viewDetails')}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        ) : (
          <Button variant="outline" className="w-full" disabled>
            Detalle no disponible
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}
