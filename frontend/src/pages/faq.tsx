'use client'

import { HelpCircle } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const faqItems = [
  {
    question: '¿Cómo detecta ForestGuard los incendios forestales?',
    answer: 'ForestGuard utiliza datos satelitales de múltiples fuentes, incluyendo MODIS (NASA) y VIIRS, que detectan puntos de calor en tiempo casi real. Estos satélites orbitan la Tierra varias veces al día, capturando imágenes térmicas que permiten identificar focos de incendio activos. La información se procesa automáticamente y se muestra en nuestra plataforma con actualizaciones cada 6-12 horas.',
  },
  {
    question: '¿Qué significa el índice FRP (Fire Radiative Power)?',
    answer: 'El FRP o Potencia Radiativa del Fuego es una medida de la intensidad de un incendio, expresada en megawatts (MW). Indica la cantidad de energía que libera el fuego por unidad de tiempo. Un FRP más alto significa un incendio más intenso. En ForestGuard, clasificamos los incendios como: Baja severidad (<100 MW), Media severidad (100-500 MW), Alta severidad (>500 MW) y Crítico (>1000 MW).',
  },
  {
    question: '¿Qué es el NDVI y por qué es importante para la recuperación?',
    answer: 'El NDVI (Índice de Vegetación de Diferencia Normalizada) es un indicador que mide la salud y densidad de la vegetación utilizando imágenes satelitales. Sus valores van de -1 a 1, donde valores cercanos a 1 indican vegetación densa y saludable. Después de un incendio, monitoreamos el NDVI para evaluar la recuperación del ecosistema. Un aumento gradual del NDVI indica que la vegetación está regenerándose.',
  },
  {
    question: '¿Cómo funciona la Ley 26.815 de Manejo del Fuego?',
    answer: 'La Ley 26.815 establece presupuestos mínimos de protección ambiental en materia de incendios forestales. Un aspecto clave es que prohíbe el cambio de uso del suelo en áreas afectadas por incendios durante un período determinado (generalmente 60 años), para evitar que los incendios sean usados como herramienta para habilitar tierras para agricultura o construcción. Nuestra herramienta de Auditoría Legal ayuda a verificar el cumplimiento de esta normativa.',
  },
  {
    question: '¿Puedo reportar un incendio que detecté personalmente?',
    answer: 'Sí, ForestGuard cuenta con un sistema de Reporte Ciudadano que permite a cualquier persona reportar actividad sospechosa o incendios detectados visualmente. El sistema incluye geolocalización, carga de fotografías y descripción del evento. Todos los reportes son revisados por autoridades competentes y pueden servir como evidencia para investigaciones sobre incendios intencionales.',
  },
]

export default function FaqPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <HelpCircle className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">Preguntas Frecuentes</h1>
          <p className="mt-2 text-muted-foreground">
            Respuestas a las consultas más comunes sobre incendios forestales y nuestra plataforma
          </p>
        </div>

        {/* FAQ Accordion */}
        <Card>
          <CardHeader>
            <CardTitle>FAQ</CardTitle>
            <CardDescription>
              Haz clic en cada pregunta para ver la respuesta
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              {faqItems.map((item, index) => (
                <AccordionItem key={index} value={`item-${index}`}>
                  <AccordionTrigger className="text-left">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground leading-relaxed">
                    {item.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>

        {/* Contact CTA */}
        <Card className="mt-6 bg-primary/5 border-primary/20">
          <CardContent className="flex flex-col items-center gap-4 py-6 text-center">
            <p className="text-foreground">
              ¿No encontraste lo que buscabas?
            </p>
            <a 
              href="/contact" 
              className="text-primary font-medium hover:underline"
            >
              Contáctanos directamente →
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
