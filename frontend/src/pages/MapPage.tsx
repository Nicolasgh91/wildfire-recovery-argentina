import { Suspense, lazy, useState } from 'react'
import { Map, List, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useI18n } from '@/context/LanguageContext'
import { fires, type Fire } from '@/data/mockdata'

const FireMap = lazy(() =>
  import('@/components/fire-map').then((mod) => ({ default: mod.FireMap })),
)

const mapFallback = (
  <div className="flex h-[calc(100vh-8rem)] items-center justify-center bg-muted">
    <div className="text-center">
      <Map className="mx-auto mb-2 h-8 w-8 animate-pulse text-primary" />
      <p className="text-sm text-muted-foreground">Loading map...</p>
    </div>
  </div>
)

export default function MapPage() {
  const { t } = useI18n()
  const [selectedFire, setSelectedFire] = useState<Fire | null>(null)
  const [showSidebar, setShowSidebar] = useState(true)

  return (
    <div className="relative h-[calc(100vh-4rem)] md:h-[calc(100vh-4rem)]">
      <Suspense fallback={mapFallback}>
        <FireMap
          fires={fires}
          selectedFire={selectedFire}
          onFireSelect={setSelectedFire}
          height="h-full"
        />
      </Suspense>

      <Button
        variant="secondary"
        size="icon"
        className="absolute left-4 top-4 z-[1000] md:hidden"
        onClick={() => setShowSidebar(!showSidebar)}
      >
        {showSidebar ? <X className="h-4 w-4" /> : <List className="h-4 w-4" />}
      </Button>

      {showSidebar && (
        <Card className="absolute right-4 top-4 z-[1000] hidden w-80 md:block">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Map className="h-5 w-5 text-primary" />
              {t('interactiveMap')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {fires.map((fire: Fire) => (
                  <button
                    key={fire.id}
                    type="button"
                    onClick={() => setSelectedFire(fire)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted ${
                      selectedFire?.id === fire.id ? 'border-primary bg-primary/10' : 'border-border'
                    }`}
                  >
                    <p className="mb-1 line-clamp-1 font-medium text-foreground">{fire.title}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{fire.province}</span>
                      <Badge
                        variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {fire.hectares.toLocaleString()} ha
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {showSidebar && (
        <Card className="absolute bottom-4 left-4 right-4 z-[1000] md:hidden">
          <CardContent className="p-3">
            <ScrollArea className="h-32">
              <div className="flex gap-2 pb-2">
                {fires.map((fire: Fire) => (
                  <button
                    key={fire.id}
                    type="button"
                    onClick={() => setSelectedFire(fire)}
                    className={`shrink-0 rounded-lg border p-2 text-left transition-colors ${
                      selectedFire?.id === fire.id ? 'border-primary bg-primary/10' : 'border-border'
                    }`}
                  >
                    <p className="w-24 truncate text-xs font-medium text-foreground">
                      {fire.province}
                    </p>
                    <Badge
                      variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                      className="mt-1 text-xs"
                    >
                      {fire.hectares.toLocaleString()} ha
                    </Badge>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
