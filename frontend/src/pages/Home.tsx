import { useMemo, useState } from 'react'
import { Trees } from 'lucide-react'
import { StoriesBar } from '@/components/stories-bar'
import { FireCard } from '@/components/fire-card'
import { FireFilters } from '@/components/fire-filters'
import { useI18n } from '@/context/LanguageContext'
import { fires } from '@/data/mockData'

export default function HomePage() {
  const { t } = useI18n()
  const [selectedProvince, setSelectedProvince] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')

  const filteredFires = useMemo(() => {
    return fires.filter((fire) => {
      const matchesProvince = selectedProvince === 'all' || fire.province === selectedProvince
      const matchesStatus = selectedStatus === 'all' || fire.status === selectedStatus
      return matchesProvince && matchesStatus
    })
  }, [selectedProvince, selectedStatus])

  return (
    <div className="min-h-screen bg-background">
      <StoriesBar fires={fires} />

      <div className="container mx-auto px-4 py-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Trees className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold text-foreground">{t('fireFeed')}</h1>
              <p className="text-sm text-muted-foreground">
                {filteredFires.length} {t('active').toLowerCase()} / {fires.length} total
              </p>
            </div>
          </div>

          <FireFilters
            selectedProvince={selectedProvince}
            selectedStatus={selectedStatus}
            onProvinceChange={setSelectedProvince}
            onStatusChange={setSelectedStatus}
          />
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredFires.map((fire) => (
            <FireCard key={fire.id} fire={fire} />
          ))}
        </div>

        {filteredFires.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Trees className="mb-4 h-16 w-16 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">
              No fires found matching your filters
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
