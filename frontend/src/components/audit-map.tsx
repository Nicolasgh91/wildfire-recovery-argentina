import { useState } from 'react'
import { Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { BaseMap } from '@/components/map/BaseMap'

interface AuditMapProps {
  onLocationSelect: (lat: number, lon: number) => void
}

// Custom marker icon
const selectedIcon = L.divIcon({
  className: 'custom-marker',
  html: `
    <div style="
      background-color: #10b981;
      width: 32px;
      height: 32px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    "></div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 32],
})

function LocationMarker({ 
  position, 
  onLocationSelect 
}: { 
  position: [number, number] | null
  onLocationSelect: (lat: number, lon: number) => void 
}) {
  useMapEvents({
    click(e) {
      onLocationSelect(e.latlng.lat, e.latlng.lng)
    },
  })

  return position ? <Marker position={position} icon={selectedIcon} /> : null
}

export function AuditMap({ onLocationSelect }: AuditMapProps) {
  const [position, setPosition] = useState<[number, number] | null>(null)

  const handleSelect = (lat: number, lon: number) => {
    setPosition([lat, lon])
    onLocationSelect(lat, lon)
  }

  return (
    <div className="h-64 w-full overflow-hidden rounded-lg border border-border">
      <BaseMap className="h-full w-full">
        <LocationMarker position={position} onLocationSelect={handleSelect} />
      </BaseMap>
    </div>
  )
}
