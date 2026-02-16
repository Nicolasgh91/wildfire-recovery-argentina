'use client'

import React, { useMemo, useState } from 'react'
import { BookOpen, Map, ClipboardCheck, FileText, Shield, Layers, Menu } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useI18n } from '@/context/LanguageContext'

interface ManualSection {
  id: string
  title: string
  resolvedTitle?: string
  icon: React.ReactNode
  content: (t: ReturnType<typeof useI18n>['t']) => React.ReactNode
}

const manualSections: ManualSection[] = [
  {
    id: 'getting-started',
    title: 'manualSectionGettingStarted',
    icon: <BookOpen className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualGettingStartedP1')}</p>
        <p className="text-muted-foreground leading-relaxed">{t('manualGettingStartedP2')}</p>
        <h3 className="font-semibold text-foreground">{t('manualRegisterAccessTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualRegisterAccess1')}</li>
          <li>{t('manualRegisterAccess2')}</li>
          <li>{t('manualRegisterAccess3')}</li>
          <li>{t('manualRegisterAccess4')}</li>
        </ol>
        <h3 className="font-semibold text-foreground">{t('manualMainNavTitle')}</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{t('manualMainNav1')}</li>
          <li>{t('manualMainNav2')}</li>
          <li>{t('manualMainNav3')}</li>
          <li>{t('manualMainNav4')}</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'fire-map',
    title: 'manualSectionFireMap',
    icon: <Map className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualMapP1')}</p>
        <h3 className="font-semibold text-foreground">{t('manualColorsTitle')}</h3>
        <ul className="space-y-2 text-muted-foreground">
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            <span>{t('manualColorLow')}</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-yellow-500" />
            <span>{t('manualColorMedium')}</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-orange-500" />
            <span>{t('manualColorHigh')}</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span>{t('manualColorCritical')}</span>
          </li>
        </ul>
        <h3 className="font-semibold text-foreground">{t('manualFeaturesTitle')}</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{t('manualFeatures1')}</li>
          <li>{t('manualFeatures2')}</li>
          <li>{t('manualFeatures3')}</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'legal-audit',
    title: 'manualSectionLegalAudit',
    icon: <ClipboardCheck className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualAuditP1')}</p>
        <h3 className="font-semibold text-foreground">{t('manualAuditHowToTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualAuditHowTo1')}</li>
          <li>{t('manualAuditHowTo2')}</li>
          <li>{t('manualAuditHowTo3')}</li>
          <li>{t('manualAuditHowTo4')}</li>
        </ol>
        <h3 className="font-semibold text-foreground">{t('manualAuditResultsTitle')}</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{t('manualAuditResults1')}</li>
          <li>{t('manualAuditResults2')}</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'reports',
    title: 'manualSectionReports',
    icon: <FileText className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualReportsP1')}</p>
        <h3 className="font-semibold text-foreground">{t('manualReportsStepsTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualReportsSteps1')}</li>
          <li>{t('manualReportsSteps2')}</li>
          <li>{t('manualReportsSteps3')}</li>
          <li>{t('manualReportsSteps4')}</li>
        </ol>
        <h3 className="font-semibold text-foreground">{t('manualReportsTipsTitle')}</h3>
        <ul className="list-disc list-inside space-y-2 text-muted-foreground">
          <li>{t('manualReportsTips1')}</li>
          <li>{t('manualReportsTips2')}</li>
          <li>{t('manualReportsTips3')}</li>
        </ul>
      </div>
    ),
  },
  {
    id: 'certificates',
    title: 'manualSectionCertificates',
    icon: <Shield className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualCertP1')}</p>
        <h3 className="font-semibold text-foreground">{t('manualCertRequestTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualCertRequest1')}</li>
          <li>{t('manualCertRequest2')}</li>
          <li>{t('manualCertRequest3')}</li>
          <li>{t('manualCertRequest4')}</li>
        </ol>
        <h3 className="font-semibold text-foreground">{t('manualCertVerifyTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualCertVerify1')}</li>
          <li>{t('manualCertVerify2')}</li>
        </ol>
      </div>
    ),
  },
  {
    id: 'episodes',
    title: 'manualSectionEpisodes',
    icon: <Layers className="h-5 w-5" />,
    content: (t) => (
      <div className="space-y-4">
        <p className="text-muted-foreground leading-relaxed">{t('manualEpisodesP1')}</p>
        <p className="text-muted-foreground leading-relaxed">{t('manualEpisodesP2')}</p>
        <h3 className="font-semibold text-foreground">{t('manualEpisodesHowTitle')}</h3>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>{t('manualEpisodesHow1')}</li>
          <li>{t('manualEpisodesHow2')}</li>
          <li>{t('manualEpisodesHow3')}</li>
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
          {section.resolvedTitle ?? section.title}
        </button>
      ))}
    </nav>
  )
}

export default function ManualPage() {
  const { t } = useI18n()

  const localizedSections = useMemo(
    () => manualSections.map((section) => ({ ...section, resolvedTitle: t(section.title as any) })),
    [t]
  )

  const [activeSection, setActiveSection] = useState(localizedSections[0].id)
  const currentSection = localizedSections.find((s) => s.id === activeSection)

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">{t('manualTitle')}</h1>
          <p className="mt-2 text-muted-foreground">
            {t('manualSubtitle')}
          </p>
        </div>

        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          <aside className="hidden w-64 shrink-0 md:block">
            <Card className="sticky top-24">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{t('manualContent')}</CardTitle>
              </CardHeader>
              <CardContent>
                <SidebarNav 
                  sections={localizedSections} 
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
                  {t('manualNavigation')}
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64">
                <div className="mt-6">
                  <h3 className="mb-4 text-sm font-semibold">{t('manualContent')}</h3>
                  <SidebarNav 
                    sections={localizedSections} 
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
                    <CardTitle>{currentSection.resolvedTitle}</CardTitle>
                  </div>
                  <CardDescription>
                    {t('manualSectionCounter')
                      .replace('{current}', String(localizedSections.findIndex((s) => s.id === activeSection) + 1))
                      .replace('{total}', String(localizedSections.length))}
                  </CardDescription>
                </CardHeader>
                <CardContent>{currentSection.content(t)}</CardContent>
              </Card>
            )}

            {/* Navigation Buttons */}
            <div className="mt-6 flex justify-between">
              <Button
                variant="outline"
                onClick={() => {
                  const currentIndex = localizedSections.findIndex((s) => s.id === activeSection)
                  if (currentIndex > 0) {
                    setActiveSection(localizedSections[currentIndex - 1].id)
                  }
                }}
                disabled={localizedSections.findIndex((s) => s.id === activeSection) === 0}
              >
                ← {t('manualPrevious')}
              </Button>
              <Button
                onClick={() => {
                  const currentIndex = localizedSections.findIndex((s) => s.id === activeSection)
                  if (currentIndex < localizedSections.length - 1) {
                    setActiveSection(localizedSections[currentIndex + 1].id)
                  }
                }}
                disabled={localizedSections.findIndex((s) => s.id === activeSection) === localizedSections.length - 1}
              >
                {t('manualNext')} →
              </Button>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
