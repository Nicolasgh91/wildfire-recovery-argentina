'use client'

import React from "react"

import { GraduationCap, Flame, Leaf, Scale } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface GlossaryTerm {
  term: string
  definition: string
  category: 'satellite' | 'environmental' | 'legal'
  icon: React.ReactNode
}

const glossaryTerms: GlossaryTerm[] = [
  {
    term: 'FRP (Fire Radiative Power)',
    definition: 'Potencia Radiativa del Fuego. Medida de la intensidad de un incendio expresada en megawatts (MW). Indica la cantidad de energía radiante liberada por el fuego por unidad de tiempo. Se utiliza para clasificar la severidad de los incendios: Baja (<100 MW), Media (100-500 MW), Alta (>500 MW), Crítica (>1000 MW).',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'NDVI (Normalized Difference Vegetation Index)',
    definition: 'Índice de Vegetación de Diferencia Normalizada. Indicador derivado de imágenes satelitales que mide la salud y densidad de la vegetación. Sus valores van de -1 a 1, donde valores cercanos a 1 indican vegetación densa y saludable, mientras que valores negativos indican agua, nieve o superficies sin vegetación.',
    category: 'environmental',
    icon: <Leaf className="h-5 w-5 text-primary" />,
  },
  {
    term: 'Ley 26.815',
    definition: 'Ley de Manejo del Fuego de Argentina. Establece presupuestos mínimos de protección ambiental en materia de incendios forestales, rurales y de interfase. Incluye disposiciones que prohíben el cambio de uso del suelo en zonas afectadas por incendios por períodos de hasta 60 años, para prevenir incendios intencionales con fines especulativos.',
    category: 'legal',
    icon: <Scale className="h-5 w-5 text-secondary" />,
  },
  {
    term: 'MODIS',
    definition: 'Moderate Resolution Imaging Spectroradiometer. Instrumento científico a bordo de los satélites Terra y Aqua de la NASA. Captura datos en 36 bandas espectrales y es fundamental para la detección de incendios activos y el monitoreo de cambios en la vegetación a escala global.',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'VIIRS',
    definition: 'Visible Infrared Imaging Radiometer Suite. Sensor a bordo de los satélites Suomi NPP y NOAA-20. Proporciona datos de mayor resolución que MODIS y es capaz de detectar incendios más pequeños y con mayor precisión geográfica.',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'Punto de Calor',
    definition: 'Anomalía térmica detectada por satélite que indica una posible actividad de fuego. No todos los puntos de calor corresponden a incendios forestales; pueden incluir quemas agrícolas controladas, actividad industrial o volcánica.',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'Área Quemada',
    definition: 'Superficie total afectada por un incendio, medida en hectáreas. Se calcula mediante análisis de imágenes satelitales comparando el estado pre y post incendio utilizando índices como NBR (Normalized Burn Ratio).',
    category: 'environmental',
    icon: <Leaf className="h-5 w-5 text-primary" />,
  },
  {
    term: 'Auditoría de Uso del Suelo',
    definition: 'Proceso de verificación del cumplimiento de la Ley 26.815 para una parcela específica. Determina si existen restricciones para el cambio de uso del suelo debido a incendios recientes en la zona.',
    category: 'legal',
    icon: <Scale className="h-5 w-5 text-secondary" />,
  },
]

const categoryColors = {
  satellite: { bg: 'bg-destructive/10', text: 'text-destructive', label: 'Satelital' },
  environmental: { bg: 'bg-primary/10', text: 'text-primary', label: 'Ambiental' },
  legal: { bg: 'bg-secondary/10', text: 'text-secondary', label: 'Legal' },
}

export default function GlossaryPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <GraduationCap className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">Glosario</h1>
          <p className="mt-2 text-muted-foreground">
            Términos técnicos utilizados en el monitoreo de incendios forestales
          </p>
        </div>

        {/* Category Legend */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-4">
          {Object.entries(categoryColors).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${value.bg}`} />
              <span className="text-sm text-muted-foreground">{value.label}</span>
            </div>
          ))}
        </div>

        {/* Terms Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {glossaryTerms.map((item) => {
            const categoryStyle = categoryColors[item.category]
            return (
              <Card key={item.term} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {item.icon}
                      <CardTitle className="text-base">{item.term}</CardTitle>
                    </div>
                    <Badge variant="outline" className={`${categoryStyle.bg} ${categoryStyle.text} border-0`}>
                      {categoryStyle.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed">
                    {item.definition}
                  </CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
