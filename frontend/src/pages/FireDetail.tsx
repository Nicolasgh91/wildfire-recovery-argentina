import { Suspense, lazy } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  AlertTriangle,
  MapPin,
  Calendar,
  Flame,
  Shield,
  FileText,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { NdviChart } from '@/components/ndvi-chart'
import { ReliabilityScore } from '@/components/reliability-score'
import { useI18n } from '@/context/LanguageContext'
import { fires } from '@/data/mockdata'
import { cn } from '@/lib/utils'

const FireMap = lazy(() =>
  import('@/components/fire-map').then((mod) => ({ default: mod.FireMap })),
)

const mapFallback = (
  <div className="flex h-64 items-center justify-center rounded-lg bg-muted">
    <p className="text-sm text-muted-foreground">Loading map...</p>
  </div>
)

export default function FireDetailPage() {
  const { t } = useI18n()
  const { id } = useParams<{ id: string }>()
  const fire = fires.find((item) => item.id === id)

  if (!fire) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-12 text-center">
          <p className="mb-4 text-lg font-semibold text-foreground">Fire not found.</p>
          <Button asChild variant="secondary">
            <Link to="/">Back to home</Link>
          </Button>
        </div>
      </div>
    )
  }

  const getLandUseStatusStyle = (status: string) => {
    switch (status) {
      case 'Prohibited Land Use':
        return 'bg-destructive/10 text-destructive border-destructive/30'
      case 'Protected Area':
        return 'bg-primary/10 text-primary border-primary/30'
      case 'Under Review':
        return 'bg-accent/20 text-accent-foreground border-accent/30'
      default:
        return 'bg-muted text-muted-foreground border-muted'
    }
  }

  const handleDownloadReport = () => {
    alert('PDF report download triggered (mock)')
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="relative">
        <div className="h-64 md:h-80">
          <Suspense fallback={mapFallback}>
            <FireMap fires={[fire]} selectedFire={fire} height="h-full" interactive={false} />
          </Suspense>
        </div>
        <Button
          asChild
          variant="secondary"
          size="sm"
          className="absolute left-4 top-4 z-[1000] gap-2"
        >
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            {t('home')}
          </Link>
        </Button>
      </div>

      <div className="container mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="mb-3 text-2xl font-bold text-foreground md:text-3xl">
            {fire.title}
          </h1>
          <div className="flex flex-wrap gap-2">
            <Badge
              variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
              className="text-sm"
            >
              {fire.severity === 'high'
                ? t('highSeverity')
                : fire.severity === 'medium'
                ? t('mediumSeverity')
                : t('lowSeverity')}
            </Badge>
            <Badge
              variant="outline"
              className={cn('text-sm', getLandUseStatusStyle(fire.landUseStatus))}
            >
              <Shield className="mr-1 h-3 w-3" />
              {fire.landUseStatus}
            </Badge>
            <Badge variant={fire.status === 'active' ? 'destructive' : 'secondary'}>
              {fire.status === 'active' ? t('active') : t('extinguished')}
            </Badge>
          </div>
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('province')}</p>
                <p className="font-semibold text-foreground">{fire.province}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-primary/10 p-2">
                <Calendar className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('date')}</p>
                <p className="font-semibold text-foreground">
                  {new Date(fire.date).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-destructive/10 p-2">
                <Flame className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('area')}</p>
                <p className="font-semibold text-foreground">
                  {fire.hectares.toLocaleString()} ha
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="rounded-lg bg-accent/20 p-2">
                <FileText className="h-5 w-5 text-accent-foreground" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Coordinates</p>
                <p className="text-sm font-semibold text-foreground">
                  {fire.lat.toFixed(4)}, {fire.lon.toFixed(4)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mb-6">
          <ReliabilityScore score={fire.reliabilityScore} />
        </div>

        <div className="mb-6">
          <NdviChart data={fire.ndviHistory} />
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button onClick={handleDownloadReport} className="gap-2">
            <Download className="h-4 w-4" />
            {t('downloadReport')}
          </Button>
          <Button asChild variant="destructive" className="w-full gap-2 sm:w-auto">
            <Link to={`/citizen-report?fire_id=${fire.id}`}>
              <AlertTriangle className="h-4 w-4" />
              {t('reportSuspicious')}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
