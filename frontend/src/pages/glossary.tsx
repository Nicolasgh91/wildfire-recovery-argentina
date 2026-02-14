'use client'

import React from 'react'

import { GraduationCap, Flame, Leaf, Scale } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useI18n } from '@/context/LanguageContext'

interface GlossaryTerm {
  term: string
  definition: string
  category: 'satellite' | 'environmental' | 'legal'
  icon: React.ReactNode
}

const glossaryTerms: GlossaryTerm[] = [
  {
    term: 'glossaryTermFrp',
    definition: 'glossaryDefFrp',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'glossaryTermNdvi',
    definition: 'glossaryDefNdvi',
    category: 'environmental',
    icon: <Leaf className="h-5 w-5 text-primary" />,
  },
  {
    term: 'glossaryTermLaw',
    definition: 'glossaryDefLaw',
    category: 'legal',
    icon: <Scale className="h-5 w-5 text-secondary" />,
  },
  {
    term: 'glossaryTermModis',
    definition: 'glossaryDefModis',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'glossaryTermViirs',
    definition: 'glossaryDefViirs',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'glossaryTermHotspot',
    definition: 'glossaryDefHotspot',
    category: 'satellite',
    icon: <Flame className="h-5 w-5 text-destructive" />,
  },
  {
    term: 'glossaryTermBurnedArea',
    definition: 'glossaryDefBurnedArea',
    category: 'environmental',
    icon: <Leaf className="h-5 w-5 text-primary" />,
  },
  {
    term: 'glossaryTermLandAudit',
    definition: 'glossaryDefLandAudit',
    category: 'legal',
    icon: <Scale className="h-5 w-5 text-secondary" />,
  },
]

const categoryStyles = {
  satellite: { bg: 'bg-destructive/10', text: 'text-destructive' },
  environmental: { bg: 'bg-primary/10', text: 'text-primary' },
  legal: { bg: 'bg-secondary/10', text: 'text-secondary' },
}

export default function GlossaryPage() {
  const { t } = useI18n()

  const categoryLabels = {
    satellite: t('glossaryCategorySatellite'),
    environmental: t('glossaryCategoryEnvironmental'),
    legal: t('glossaryCategoryLegal'),
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <GraduationCap className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">{t('glossaryTitle')}</h1>
          <p className="mt-2 text-muted-foreground">
            {t('glossarySubtitle')}
          </p>
        </div>

        {/* Category Legend */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-4">
          {Object.entries(categoryStyles).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <span className={`h-3 w-3 rounded-full ${value.bg}`} />
              <span className="text-sm text-muted-foreground">{categoryLabels[key as keyof typeof categoryLabels]}</span>
            </div>
          ))}
        </div>

        {/* Terms Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {glossaryTerms.map((item) => {
            const categoryStyle = categoryStyles[item.category]
            return (
              <Card key={item.term} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {item.icon}
                      <CardTitle className="text-base">{t(item.term as any)}</CardTitle>
                    </div>
                    <Badge variant="outline" className={`${categoryStyle.bg} ${categoryStyle.text} border-0`}>
                      {categoryLabels[item.category]}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed">
                    {t(item.definition as any)}
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
