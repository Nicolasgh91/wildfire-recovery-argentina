import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area'
import { useI18n } from '@/context/LanguageContext'
import type { EpisodeListItem } from '@/types/episode'

const FRP_MEDIUM_THRESHOLD = 20
const FRP_HIGH_THRESHOLD = 50

const resolveSeverity = (maxFrp?: number | null) => {
  if (maxFrp === null || maxFrp === undefined || Number.isNaN(maxFrp)) return 'low'
  if (maxFrp >= FRP_HIGH_THRESHOLD) return 'high'
  if (maxFrp >= FRP_MEDIUM_THRESHOLD) return 'medium'
  return 'low'
}

interface StoriesBarProps {
  fires: EpisodeListItem[]
}

export function StoriesBar({ fires }: StoriesBarProps) {
  const { t } = useI18n()
  const highSeverityFires = fires.filter(
    (f) => resolveSeverity(f.frp_max) === 'high' && (f.status ?? 'active') === 'active'
  )

  if (highSeverityFires.length === 0) return null

  return (
    <div className="border-b border-border bg-card py-4">
      <div className="container mx-auto px-4">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-destructive">
          <Flame className="h-4 w-4" />
          {t('urgentFires')}
        </h2>
        <ScrollArea className="w-full whitespace-nowrap">
          <div className="flex gap-4">
            {highSeverityFires.map((fire) => (
              <Link
                key={fire.id}
                to={`/fires/${fire.representative_event_id ?? fire.id}`}
                className="group flex flex-col items-center gap-2"
              >
                <div className="relative h-16 w-16 overflow-hidden rounded-full bg-gradient-to-br from-destructive/80 to-destructive p-0.5">
                  <div className="flex h-full w-full items-center justify-center rounded-full bg-card transition-transform group-hover:scale-95">
                    <Flame className="h-6 w-6 text-destructive" />
                  </div>
                </div>
                <span className="max-w-[80px] truncate text-xs text-muted-foreground">
                  {fire.provinces?.[0] ?? 'Sin provincia'}
                </span>
              </Link>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>
    </div>
  )
}
