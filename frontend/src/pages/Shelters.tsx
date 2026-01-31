import { useEffect, useMemo, useState } from 'react'
import { Mountain, Users, Calendar, Wifi, WifiOff, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useI18n } from '@/context/LanguageContext'
import { shelters as mockShelters, type Shelter } from '@/data/mockdata'

type ShelterOption = Shelter & { id: string }

type VisitorLogPayload = {
  shelter_id: string
  visit_date: string
  registration_type: 'day_entry' | 'overnight'
  group_leader_name: string
  contact_email?: string
  contact_phone?: string
  companions: Array<{ full_name: string }>
}

export default function SheltersPage() {
  const { t } = useI18n()
  const [isOnline, setIsOnline] = useState(true)
  const [selectedShelter, setSelectedShelter] = useState('')
  const [hikerName, setHikerName] = useState('')
  const [groupSize, setGroupSize] = useState('')
  const [checkInDate, setCheckInDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [shelterOptions, setShelterOptions] = useState<ShelterOption[]>([])
  const [syncMessage, setSyncMessage] = useState('')

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    setIsOnline(navigator.onLine)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    const loadShelters = async () => {
      try {
        const response = await fetch('/api/v1/shelters')
        if (!response.ok) throw new Error('Failed to load shelters')
        const data = await response.json()
        if (Array.isArray(data.shelters)) {
          setShelterOptions(data.shelters)
          return
        }
      } catch {
        setShelterOptions(mockShelters)
      }
    }
    loadShelters()
  }, [])

  useEffect(() => {
    const syncOfflineLogs = async () => {
      if (!isOnline) return
      const queue = JSON.parse(localStorage.getItem('visitorLogQueue') || '[]') as VisitorLogPayload[]
      if (!queue.length) return

      const remaining: VisitorLogPayload[] = []
      for (const item of queue) {
        try {
          const response = await fetch('/api/v1/visitor-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item),
          })
          if (!response.ok) {
            remaining.push(item)
          }
        } catch {
          remaining.push(item)
        }
      }

      localStorage.setItem('visitorLogQueue', JSON.stringify(remaining))
      setSyncMessage(remaining.length ? t('offline') : t('online'))
    }

    syncOfflineLogs()
  }, [isOnline, t])

  const registrationType = useMemo(() => {
    const size = parseInt(groupSize, 10)
    return size > 1 ? 'overnight' : 'day_entry'
  }, [groupSize])

  const handleCheckIn = async () => {
    if (!selectedShelter || !hikerName || !groupSize || !checkInDate) return

    setIsSubmitting(true)

    const payload: VisitorLogPayload = {
      shelter_id: selectedShelter,
      visit_date: checkInDate,
      registration_type: registrationType,
      group_leader_name: hikerName,
      companions: Array.from({ length: Math.max(parseInt(groupSize, 10) - 1, 0) }).map(() => ({
        full_name: 'Companion',
      })),
    }

    if (isOnline) {
      await fetch('/api/v1/visitor-logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      const offlineQueue = JSON.parse(localStorage.getItem('visitorLogQueue') || '[]')
      offlineQueue.push(payload)
      localStorage.setItem('visitorLogQueue', JSON.stringify(offlineQueue))
    }

    setIsSubmitting(false)
    setShowSuccess(true)

    setSelectedShelter('')
    setHikerName('')
    setGroupSize('')
    setCheckInDate('')

    setTimeout(() => setShowSuccess(false), 3000)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto max-w-2xl px-4 py-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Mountain className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mb-2 text-3xl font-bold text-foreground">{t('visitorLog')}</h1>
          <p className="text-muted-foreground">Register your visit to mountain shelters</p>
        </div>

        <Card className={`mb-6 ${isOnline ? 'border-primary/50' : 'border-accent/50'}`}>
          <CardContent className="flex items-center gap-3 py-4">
            {isOnline ? (
              <>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                  <Wifi className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-primary">
                    {t('syncStatus')}: {t('online')}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {syncMessage || 'Data will sync immediately'}
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20">
                  <WifiOff className="h-5 w-5 text-accent-foreground" />
                </div>
                <div>
                  <p className="font-medium text-accent-foreground">
                    {t('syncStatus')}: {t('offline')}
                  </p>
                  <p className="text-sm text-muted-foreground">Data will sync when online</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {showSuccess && (
          <Alert className="mb-6 border-primary/50 bg-primary/10">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            <AlertTitle className="text-primary">{t('checkInSuccess')}</AlertTitle>
            <AlertDescription>
              Your check-in has been {isOnline ? 'submitted' : 'saved locally'}.
            </AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mountain className="h-5 w-5 text-primary" />
              {t('checkIn')}
            </CardTitle>
            <CardDescription>Fill in your details to register your visit</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="shelter">{t('shelterName')}</Label>
              <Select value={selectedShelter} onValueChange={setSelectedShelter}>
                <SelectTrigger id="shelter">
                  <SelectValue placeholder="Select a shelter" />
                </SelectTrigger>
                <SelectContent>
                  {shelterOptions.map((shelter: Shelter) => (
                    <SelectItem key={shelter.id} value={shelter.id}>
                      {shelter.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="hikerName">{t('hikerName')}</Label>
              <Input
                id="hikerName"
                placeholder="Your full name"
                value={hikerName}
                onChange={(e) => setHikerName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="groupSize">{t('groupSize')}</Label>
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <Input
                  id="groupSize"
                  type="number"
                  min="1"
                  max="50"
                  placeholder="1"
                  value={groupSize}
                  onChange={(e) => setGroupSize(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="date">{t('date')}</Label>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <Input
                  id="date"
                  type="date"
                  value={checkInDate}
                  onChange={(e) => setCheckInDate(e.target.value)}
                />
              </div>
            </div>

            <Button
              onClick={handleCheckIn}
              disabled={!selectedShelter || !hikerName || !groupSize || !checkInDate || isSubmitting}
              className="w-full gap-2"
            >
              {isSubmitting ? (
                'Processing...'
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  {t('checkIn')}
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
