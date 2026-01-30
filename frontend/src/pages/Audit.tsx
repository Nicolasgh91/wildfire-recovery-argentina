import { Suspense, lazy, useState } from 'react'
import { ClipboardCheck, MapPin, AlertTriangle, CheckCircle2, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useI18n } from '@/context/LanguageContext'
import { runAudit } from '@/data/mockdata'

const AuditMap = lazy(() =>
  import('@/components/audit-map').then((mod) => ({ default: mod.AuditMap })),
)

const mapFallback = (
  <div className="flex h-64 items-center justify-center rounded-lg bg-muted">
    <p className="text-sm text-muted-foreground">Loading map...</p>
  </div>
)

interface AuditResult {
  restricted: boolean
  message: string
  expiry?: string
}

export default function AuditPage() {
  const { t } = useI18n()
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [result, setResult] = useState<AuditResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showMapPicker, setShowMapPicker] = useState(false)

  const handleAudit = async () => {
    if (!lat || !lon) return

    setIsLoading(true)
    setResult(null)

    await new Promise((resolve) => setTimeout(resolve, 1500))

    const auditResult = runAudit(parseFloat(lat), parseFloat(lon))
    setResult(auditResult)
    setIsLoading(false)
  }

  const handleMapSelect = (latitude: number, longitude: number) => {
    setLat(latitude.toFixed(6))
    setLon(longitude.toFixed(6))
    setShowMapPicker(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <ClipboardCheck className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('landUseAudit')}</h1>
          <p className="text-muted-foreground">{t('auditDescription')}</p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              Location Input
            </CardTitle>
            <CardDescription>
              Enter coordinates manually or pick a location on the map
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="latitude">{t('latitude')}</Label>
                <Input
                  id="latitude"
                  type="number"
                  step="any"
                  placeholder="-38.4161"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="longitude">{t('longitude')}</Label>
                <Input
                  id="longitude"
                  type="number"
                  step="any"
                  placeholder="-63.6167"
                  value={lon}
                  onChange={(e) => setLon(e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                variant="outline"
                onClick={() => setShowMapPicker(!showMapPicker)}
                className="gap-2"
              >
                <MapPin className="h-4 w-4" />
                {showMapPicker ? 'Hide Map' : t('pickOnMap')}
              </Button>
              <Button
                onClick={handleAudit}
                disabled={!lat || !lon || isLoading}
                className="gap-2"
              >
                {isLoading ? (
                  <>
                    <Search className="h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    {t('runAudit')}
                  </>
                )}
              </Button>
            </div>

            {showMapPicker && (
              <div className="mt-4">
                <p className="mb-2 text-sm text-muted-foreground">
                  Click on the map to select a location
                </p>
                <Suspense fallback={mapFallback}>
                  <AuditMap onLocationSelect={handleMapSelect} />
                </Suspense>
              </div>
            )}
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>{t('auditResult')}</CardTitle>
            </CardHeader>
            <CardContent>
              {result.restricted ? (
                <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
                  <AlertTriangle className="h-5 w-5" />
                  <AlertTitle className="text-lg font-semibold">
                    {t('constructionProhibited')}
                  </AlertTitle>
                  <AlertDescription className="mt-2">
                    <p className="mb-2">{result.message}</p>
                    {result.expiry && (
                      <p className="font-semibold">
                        {t('prohibitedUntil')}: {new Date(result.expiry).toLocaleDateString()}
                      </p>
                    )}
                  </AlertDescription>
                </Alert>
              ) : (
                <Alert className="border-primary/50 bg-primary/10">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <AlertTitle className="text-lg font-semibold text-primary">
                    {t('noRestrictionsFound')}
                  </AlertTitle>
                  <AlertDescription className="mt-2 text-foreground">
                    {result.message}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
