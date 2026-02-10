'use client'

import React from "react"

import { useState } from 'react'
import { BookOpen, Map, ClipboardCheck, FileText, Shield, Menu } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'

interface ManualSection {
  id: string
  title: string
  icon: React.ReactNode
  content: React.ReactNode
}

const manualSections: ManualSection[] = [
  {
    id: 'getting-started',
    title: 'Primeros Pasos',
    icon: <BookOpen className="h-5 w-5" />,
    content: (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">
          Bienvenido a ForestGuard, la plataforma de monitoreo y recuperación de incendios forestales de Argentina. 
          Esta guía te ayudará a aprovechar todas las funcionalidades disponibles.
        </p>
        <h3 className="font-semibold text-foreground">Registro y Acceso</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>Accede a la página de inicio de ForestGuard</li>
          <li>Haz clic en &quot;Iniciar Sesión&quot; en la barra de navegación</li>
          <li>Ingresa tu correo electrónico y contraseña</li>
          <li>Para cuentas de administrador, usa un email con dominio @forestguard.ar</li>
        </ol>
        <h3 className="font-semibold text-foreground">Navegación Principal</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li><strong>Inicio:</strong> Feed de incendios activos con filtros</li>
          <li><strong>Mapa:</strong> Visualización geográfica interactiva</li>
          <li><strong>Auditoría:</strong> Verificación de restricciones legales</li>
          <li><strong>Certificados:</strong> Emisión y verificación de documentos</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'fire-map',
    title: 'Mapa de Incendios',
    icon: <Map className="h-5 w-5" />,
    content: (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">
          El mapa interactivo muestra todos los incendios detectados en Argentina en tiempo casi real.
        </p>
        <h3 className="font-semibold text-foreground">Interpretación de Colores</h3>
        <ul className="space-y-2 text-muted-foreground">
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            <span><strong>Verde:</strong> Baja severidad (FRP menor a 100 MW)</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-yellow-500" />
            <span><strong>Amarillo:</strong> Media severidad (FRP 100-500 MW)</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-orange-500" />
            <span><strong>Naranja:</strong> Alta severidad (FRP 500-1000 MW)</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span><strong>Rojo:</strong> Crítico (FRP mayor a 1000 MW)</span>
          </li>
        </ul>
        <h3 className="font-semibold text-foreground">Funcionalidades</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>Haz clic en un marcador para ver detalles del incendio</li>
          <li>Usa los filtros laterales para filtrar por provincia o severidad</li>
          <li>El zoom te permite explorar áreas específicas</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'legal-audit',
    title: 'Auditoría Legal',
    icon: <ClipboardCheck className="h-5 w-5" />,
    content: (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">
          La herramienta de Auditoría Legal permite verificar si una parcela tiene restricciones de uso del suelo 
          según la Ley 26.815 de Manejo del Fuego.
        </p>
        <h3 className="font-semibold text-foreground">Cómo realizar una auditoría</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>Ingresa las coordenadas (latitud y longitud) de la parcela</li>
          <li>Alternativamente, usa el botón &quot;Seleccionar en Mapa&quot;</li>
          <li>Haz clic en &quot;Ejecutar Auditoría&quot;</li>
          <li>El sistema verificará si hay incendios registrados en la zona</li>
        </ol>
        <h3 className="font-semibold text-foreground">Resultados posibles</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li><strong>Sin restricciones:</strong> No hay incendios recientes que afecten la parcela</li>
          <li><strong>Construcción prohibida:</strong> La parcela está dentro de una zona afectada y tiene restricciones temporales</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'reports',
    title: 'Reportes Ciudadanos',
    icon: <FileText className="h-5 w-5" />,
    content: (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">
          El sistema de reportes permite a cualquier ciudadano informar sobre actividad sospechosa 
          relacionada con incendios forestales.
        </p>
        <h3 className="font-semibold text-foreground">Pasos para crear un reporte</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li><strong>Ubicación:</strong> Selecciona el punto exacto en el mapa donde observaste la actividad</li>
          <li><strong>Fotografía:</strong> Sube una imagen como evidencia (opcional pero recomendado)</li>
          <li><strong>Descripción:</strong> Detalla lo que observaste con la mayor precisión posible</li>
          <li><strong>Envío:</strong> Confirma y envía el reporte para revisión</li>
        </ol>
        <h3 className="font-semibold text-foreground">Recomendaciones</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>Incluye fecha y hora aproximada de la observación</li>
          <li>Describe cualquier vehículo o persona involucrada</li>
          <li>No te pongas en riesgo para obtener evidencia</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'certificates',
    title: 'Certificados',
    icon: <Shield className="h-5 w-5" />,
    content: (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">
          El Centro de Certificados permite solicitar y verificar documentos oficiales 
          sobre el estado de uso del suelo de una parcela.
        </p>
        <h3 className="font-semibold text-foreground">Solicitar un Certificado</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>Accede al Centro de Certificados (requiere autenticación)</li>
          <li>Ingresa el ID Catastral de la parcela</li>
          <li>Completa el nombre del propietario</li>
          <li>El sistema generará un certificado con un código único</li>
        </ol>
        <h3 className="font-semibold text-foreground">Verificar un Certificado</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>Ingresa el código del certificado en la pestaña &quot;Verificar&quot;</li>
          <li>El sistema confirmará si es válido y mostrará los detalles</li>
        </ol>
      </div>
    ),
  },
]

function SidebarNav({ 
  sections, 
  activeSection, 
  onSelect 
}: { 
  sections: ManualSection[]
  activeSection: string
  onSelect: (id: string) => void 
}) {
  return (
    <nav className="flex flex-col gap-1">
      {sections.map((section) => (
        <button
          key={section.id}
          onClick={() => onSelect(section.id)}
          className={cn(
            'flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors',
            activeSection === section.id
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          )}
        >
          {section.icon}
          {section.title}
        </button>
      ))}
    </nav>
  )
}

export default function ManualPage() {
  const [activeSection, setActiveSection] = useState(manualSections[0].id)
  const currentSection = manualSections.find((s) => s.id === activeSection)

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">Manual de Usuario</h1>
          <p className="mt-2 text-muted-foreground">
            Guía completa para utilizar ForestGuard
          </p>
        </div>

        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          <aside className="hidden w-64 shrink-0 md:block">
            <Card className="sticky top-24">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Contenido</CardTitle>
              </CardHeader>
              <CardContent>
                <SidebarNav 
                  sections={manualSections} 
                  activeSection={activeSection}
                  onSelect={setActiveSection}
                />
              </CardContent>
            </Card>
          </aside>

          {/* Mobile Sidebar */}
          <div className="mb-4 md:hidden">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" className="w-full bg-transparent">
                  <Menu className="mr-2 h-4 w-4" />
                  Navegación
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64">
                <div className="mt-6">
                  <h3 className="mb-4 text-sm font-semibold">Contenido</h3>
                  <SidebarNav 
                    sections={manualSections} 
                    activeSection={activeSection}
                    onSelect={(id) => {
                      setActiveSection(id)
                    }}
                  />
                </div>
              </SheetContent>
            </Sheet>
          </div>

          {/* Content */}
          <main className="flex-1">
            {currentSection && (
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <span className="text-primary">{currentSection.icon}</span>
                    <CardTitle>{currentSection.title}</CardTitle>
                  </div>
                  <CardDescription>
                    Sección {manualSections.findIndex((s) => s.id === activeSection) + 1} de {manualSections.length}
                  </CardDescription>
                </CardHeader>
                <CardContent>{currentSection.content}</CardContent>
              </Card>
            )}

            {/* Navigation Buttons */}
            <div className="mt-6 flex justify-between">
              <Button
                variant="outline"
                onClick={() => {
                  const currentIndex = manualSections.findIndex((s) => s.id === activeSection)
                  if (currentIndex > 0) {
                    setActiveSection(manualSections[currentIndex - 1].id)
                  }
                }}
                disabled={manualSections.findIndex((s) => s.id === activeSection) === 0}
              >
                ← Anterior
              </Button>
              <Button
                onClick={() => {
                  const currentIndex = manualSections.findIndex((s) => s.id === activeSection)
                  if (currentIndex < manualSections.length - 1) {
                    setActiveSection(manualSections[currentIndex + 1].id)
                  }
                }}
                disabled={manualSections.findIndex((s) => s.id === activeSection) === manualSections.length - 1}
              >
                Siguiente →
              </Button>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
