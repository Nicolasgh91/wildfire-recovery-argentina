import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useI18n } from '@/context/LanguageContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { Fire } from '@/data/mockdata'
import 'leaflet/dist/leaflet.css'

interface FireMapProps {
  fires: Fire[]
  selectedFire?: Fire | null
  onFireSelect?: (fire: Fire) => void
  height?: string
  interactive?: boolean
}

// Custom marker icons
function createFireIcon(severity: Fire['severity']) {
  const colors = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#10b981',
  }

  return L.divIcon({
    className: 'custom-fire-marker',
    html: `
      <div style="
        background-color: ${colors[severity]};
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="white" stroke="white" strokeWidth="2">
          <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
        </svg>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  })
}

// Component to handle map center updates
function MapUpdater({ center }: { center: [number, number] }) {
  const map = useMap()
  
  useEffect(() => {
    map.setView(center, map.getZoom())
  }, [center, map])
  
  return null
}

export function FireMap({ 
  fires, 
  selectedFire, 
  onFireSelect, 
  height = 'h-[calc(100vh-8rem)]',
  interactive = true 
}: FireMapProps) {
  const { t } = useI18n()
  
  // Center map on Argentina
  const defaultCenter: [number, number] = [-38.4161, -63.6167]
  const center = selectedFire 
    ? [selectedFire.lat, selectedFire.lon] as [number, number]
    : defaultCenter

  return (
    <div className={`${height} w-full overflow-hidden rounded-lg border border-border`}>
      <MapContainer
        center={center}
        zoom={5}
        scrollWheelZoom={interactive}
        dragging={interactive}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {selectedFire && <MapUpdater center={[selectedFire.lat, selectedFire.lon]} />}
        
        {fires.map((fire) => (
          <Marker
            key={fire.id}
            position={[fire.lat, fire.lon]}
            icon={createFireIcon(fire.severity)}
            eventHandlers={{
              click: () => onFireSelect?.(fire),
            }}
          >
            <Popup>
              <div className="min-w-[200px] p-2">
                <h3 className="mb-2 font-semibold">{fire.title}</h3>
                <div className="mb-3 flex flex-wrap gap-2">
                  <Badge 
                    variant={fire.severity === 'high' ? 'destructive' : 'secondary'}
                    className="text-xs"
                  >
                    {fire.severity === 'high' ? t('highSeverity') : 
                     fire.severity === 'medium' ? t('mediumSeverity') : t('lowSeverity')}
                  </Badge>
                </div>
                <div className="mb-3 space-y-1 text-sm text-muted-foreground">
                  <p>{t('area')}: {fire.hectares.toLocaleString()} ha</p>
                  <p>{t('province')}: {fire.province}</p>
                </div>
                <Button asChild size="sm" className="w-full">
                  <Link to={`/fires/${fire.id}`}>{t('viewDetails')}</Link>
                </Button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
