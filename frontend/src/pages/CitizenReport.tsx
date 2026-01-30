import { Suspense, lazy, useState, type ChangeEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  MapPin,
  Upload,
  FileText,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useI18n } from '@/context/LanguageContext'
import { fires } from '@/data/mockdata'

const AuditMap = lazy(() =>
  import('@/components/audit-map').then((mod) => ({ default: mod.AuditMap })),
)

const mapFallback = (
  <div className="flex h-48 items-center justify-center rounded-lg bg-muted">
    <p className="text-sm text-muted-foreground">Loading map...</p>
  </div>
)

function CitizenReportContent() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fireId = searchParams.get('fire_id')
  const preselectedFire = fireId ? fires.find((f) => f.id === fireId) : null

  const [step, setStep] = useState(1)
  const [selectedLocation, setSelectedLocation] = useState<{ lat: number; lon: number } | null>(
    preselectedFire ? { lat: preselectedFire.lat, lon: preselectedFire.lon } : null,
  )
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [description, setDescription] = useState('')
  const [isSubmitted, setIsSubmitted] = useState(false)

  const steps = [
    { number: 1, label: t('selectLocation'), icon: MapPin },
    { number: 2, label: t('uploadPhoto'), icon: Upload },
    { number: 3, label: t('description'), icon: FileText },
    { number: 4, label: t('submitReport'), icon: CheckCircle2 },
  ]

  const handleLocationSelect = (lat: number, lon: number) => {
    setSelectedLocation({ lat, lon })
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadedFile(e.target.files[0])
    }
  }

  const handleSubmit = async () => {
    await new Promise((resolve) => setTimeout(resolve, 1500))
    setIsSubmitted(true)
  }

  const canProceed = () => {
    switch (step) {
      case 1:
        return selectedLocation !== null
      case 2:
        return true
      case 3:
        return description.trim().length > 10
      default:
        return true
    }
  }

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container mx-auto max-w-2xl px-4 py-16">
          <Card className="border-primary/50 bg-primary/5">
            <CardContent className="pt-6 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/20">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
              <h2 className="mb-2 text-2xl font-bold text-primary">{t('reportSuccess')}</h2>
              <p className="text-muted-foreground">{t('reportSuccessMessage')}</p>
              <Button className="mt-6" onClick={() => navigate('/')}>
                {t('home')}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-2xl px-4 py-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('citizenReport')}</h1>
          <p className="text-muted-foreground">{t('reportWizard')}</p>
        </div>

        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((s, index) => (
              <div key={s.number} className="flex flex-1 items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors ${
                      step >= s.number
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-muted bg-background text-muted-foreground'
                    }`}
                  >
                    {s.icon && <s.icon className="h-5 w-5" />}
                  </div>
                  <span className="mt-2 hidden text-xs text-muted-foreground sm:block">
                    {s.label}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 flex-1 transition-colors ${
                      step > s.number ? 'bg-primary' : 'bg-muted'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {steps[step - 1].icon &&
                steps[step - 1].icon({ className: 'h-5 w-5 text-primary' })}
              Step {step}: {steps[step - 1].label}
            </CardTitle>
            <CardDescription>
              {step === 1 && 'Select the location where you observed suspicious activity'}
              {step === 2 && 'Upload a photo as evidence (optional)'}
              {step === 3 && 'Describe what you observed in detail'}
              {step === 4 && 'Review and submit your report'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === 1 && (
              <div className="space-y-4">
                {preselectedFire && (
                  <Alert className="border-primary/50 bg-primary/10">
                    <MapPin className="h-4 w-4 text-primary" />
                    <AlertTitle className="text-primary">Location Pre-selected</AlertTitle>
                    <AlertDescription>
                      Report for: {preselectedFire.title}
                    </AlertDescription>
                  </Alert>
                )}
                <Suspense fallback={mapFallback}>
                  <AuditMap onLocationSelect={handleLocationSelect} />
                </Suspense>
                {selectedLocation && (
                  <p className="text-sm text-muted-foreground">
                    Selected: {selectedLocation.lat.toFixed(4)}, {selectedLocation.lon.toFixed(4)}
                  </p>
                )}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted p-8 transition-colors hover:border-primary">
                  <Upload className="mb-4 h-12 w-12 text-muted-foreground" />
                  <label className="cursor-pointer">
                    <span className="text-primary underline">Click to upload</span>
                    <input
                      type="file"
                      className="hidden"
                      accept="image/*"
                      onChange={handleFileChange}
                    />
                  </label>
                  <p className="mt-2 text-sm text-muted-foreground">PNG, JPG up to 10MB</p>
                </div>
                {uploadedFile && (
                  <Alert className="border-primary/50 bg-primary/10">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    <AlertTitle className="text-primary">File Selected</AlertTitle>
                    <AlertDescription>{uploadedFile.name}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {step === 3 && (
              <Textarea
                placeholder={t('descriptionPlaceholder')}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="min-h-[200px]"
              />
            )}

            {step === 4 && (
              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <h4 className="mb-2 font-semibold text-foreground">Report Summary</h4>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p>
                      <strong>Location:</strong>{' '}
                      {selectedLocation
                        ? `${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lon.toFixed(4)}`
                        : 'Not selected'}
                    </p>
                    <p>
                      <strong>Photo:</strong> {uploadedFile ? uploadedFile.name : 'None'}
                    </p>
                    <p>
                      <strong>Description:</strong> {description || 'None'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-6 flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep(step - 1)}
                disabled={step === 1}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                {t('previous')}
              </Button>
              {step < 4 ? (
                <Button
                  onClick={() => setStep(step + 1)}
                  disabled={!canProceed()}
                  className="gap-2"
                >
                  {t('next')}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button onClick={handleSubmit} className="gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  {t('submitReport')}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function CitizenReportPage() {
  return <CitizenReportContent />
}
