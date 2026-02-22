'use client'

import { HelpCircle } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useI18n } from '@/context/LanguageContext'

const faqItems = [
  { question: 'faqQ1', answer: 'faqA1' },
  { question: 'faqQ2', answer: 'faqA2' },
  { question: 'faqQ3', answer: 'faqA3' },
  { question: 'faqQ4', answer: 'faqA4' },
  { question: 'faqQ5', answer: 'faqA5' },
  { question: 'faqQ6', answer: 'faqA6' },
  { question: 'faqQ7', answer: 'faqA7' },
  { question: 'faqQ8', answer: 'faqA8' },
  { question: 'faqQ9', answer: 'faqA9' },
  { question: 'faqQ10', answer: 'faqA10' },
  { question: 'faqQ11', answer: 'faqA11' },
]

export default function FaqPage() {
  const { t } = useI18n()

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <HelpCircle className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">{t('faqTitle')}</h1>
          <p className="mt-2 text-muted-foreground">
            {t('faqSubtitle')}
          </p>
        </div>

        {/* FAQ Accordion */}
        <Card>
          <CardHeader>
            <CardTitle>FAQ</CardTitle>
            <CardDescription>
              {t('faqHint')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              {faqItems.map((item, index) => (
                <AccordionItem key={index} value={`item-${index}`}>
                  <AccordionTrigger className="text-left">
                    {t(item.question as any)}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground leading-relaxed">
                    {t(item.answer as any)}
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
              {t('faqCtaPrompt')}
            </p>
            <a 
              href="/contact" 
              className="text-primary font-medium hover:underline"
            >
              {t('faqCtaAction')} →
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
