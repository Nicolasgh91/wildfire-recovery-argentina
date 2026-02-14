import * as React from 'react'
import { Link } from 'react-router-dom'
import { Trees, Map, ClipboardCheck, FileText, HelpCircle, BookOpen, GraduationCap, Mail, ExternalLink, AlertTriangle, History as HistoryIcon } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useI18n } from '@/context/LanguageContext'

export function Footer() {
  const { t } = useI18n()
  const [pendingHref, setPendingHref] = React.useState<string | null>(null)

  const productLinks = [
    { href: '/fires/history', label: t('footerLinkHistory'), icon: HistoryIcon },
    { href: '/map', label: t('footerLinkMap'), icon: Map },
    { href: '/audit', label: t('footerLinkAudit'), icon: ClipboardCheck },
    { href: '/exploracion', label: t('footerLinkExploration'), icon: FileText },
  ]

  const supportLinks = [
    { href: '/faq', label: t('footerLinkFaq'), icon: HelpCircle },
    { href: '/manual', label: t('footerLinkManual'), icon: BookOpen },
    { href: '/glossary', label: t('footerLinkGlossary'), icon: GraduationCap },
  ]

  const companyLinks = [
    { href: '/contact', label: t('footerLinkContact'), icon: Mail },
    { href: 'https://forestguard.freedynamicdns.org/docs', label: t('footerLinkApiDocs'), icon: ExternalLink, external: true },
    { href: 'https://www.argentina.gob.ar/parquesnacionales', label: t('footerExternalProtectedAreasLabel'), icon: ExternalLink, external: true, tooltip: t('footerExternalProtectedAreasTooltip') },
    { href: 'https://www.argentina.gob.ar/reporte-diario-de-incendios', label: t('footerExternalDailyReportLabel'), icon: ExternalLink, external: true, tooltip: t('footerExternalDailyReportTooltip') },
  ]

  const PUBLIC_SOURCES_AR = [
    { label: t('footerExternalSnmfLabel'), href: 'https://www.argentina.gob.ar/servicio-nacional-de-manejo-del-fuego', tooltip: t('footerExternalSnmfTooltip') },
    [
      { label: t('footerExternalBoletinLabel'), href: 'https://www.boletinoficial.gob.ar/', tooltip: t('footerExternalBoletinTooltip') },
      { label: t('footerExternalConaeLabel'), href: 'https://catalogos5.conae.gov.ar/catalogofocos/', tooltip: t('footerExternalConaeTooltip') },
    ],
    { label: t('footerExternalSmnLabel'), href: 'https://ws2.smn.gob.ar/', tooltip: t('footerExternalSmnTooltip') },
    [
      { label: t('footerExternalSpmfLabel'), href: 'https://bosques.chubut.gov.ar/manejo-del-fuego/', tooltip: t('footerExternalSpmfTooltip') },
      { label: t('footerExternalSplifLabel'), href: 'https://splif.rionegro.gov.ar/', tooltip: t('footerExternalSplifTooltip') },
    ],
  ]

  const handleExternalClick = (href: string) => {
    setPendingHref(href)
  }

  const confirmNavigation = () => {
    if (pendingHref) {
      window.open(pendingHref, '_blank', 'noopener,noreferrer')
      setPendingHref(null)
    }
  }

  const cancelNavigation = () => {
    setPendingHref(null)
  }

  return (
    <footer className="hidden md:block border-t border-border bg-card">
      <div className="container mx-auto px-6 py-12">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-5">
          {/* Brand */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Trees className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold text-foreground">ForestGuard</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {t('footerBrandLine1')}
              {' '}
              {t('footerBrandLine2')}
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">
              {t('footerProduct')}
            </h3>
            <ul className="flex flex-col gap-3">
              {productLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    onClick={() => window.scrollTo(0, 0)}
                    className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary"
                  >
                    <link.icon className="h-4 w-4" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">
              {t('footerSupport')}
            </h3>
            <ul className="flex flex-col gap-3">
              {supportLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    onClick={() => window.scrollTo(0, 0)}
                    className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary"
                  >
                    <link.icon className="h-4 w-4" />
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">
              {t('footerInformative')}
            </h3>
            <ul className="flex flex-col gap-3">
              {companyLinks.map((link) => (
                <li key={link.href}>
                  {'tooltip' in link ? (
                    <TooltipProvider>
                      <Tooltip delayDuration={300}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => handleExternalClick(link.href)}
                            className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary text-left"
                          >
                            <link.icon className="h-4 w-4" />
                            <span className="truncate">{link.label}</span>
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{link.tooltip}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ) : 'external' in link && link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary"
                    >
                      <link.icon className="h-4 w-4" />
                      {link.label}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      onClick={() => window.scrollTo(0, 0)}
                      className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary"
                    >
                      <link.icon className="h-4 w-4" />
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Public Sources (Argentina) */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">
              {t('footerPublicSources')}
            </h3>
            <TooltipProvider>
              <ul className="flex flex-col gap-3">
                {PUBLIC_SOURCES_AR.map((item, index) => {
                  if (Array.isArray(item)) {
                    return (
                      <li key={`group-${index}`} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <ExternalLink className="h-3 w-3 shrink-0" />
                        <div className="flex items-center gap-2">
                          {item.map((link, subIndex) => (
                            <React.Fragment key={link.href}>
                              <Tooltip delayDuration={300}>
                                <TooltipTrigger asChild>
                                  <button
                                    onClick={() => handleExternalClick(link.href)}
                                    className="transition-colors hover:text-primary text-left truncate"
                                  >
                                    {link.label}
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{link.tooltip}</p>
                                </TooltipContent>
                              </Tooltip>
                              {subIndex < item.length - 1 && <span>|</span>}
                            </React.Fragment>
                          ))}
                        </div>
                      </li>
                    )
                  }

                  return (
                    <li key={item.href}>
                      <Tooltip delayDuration={300}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => handleExternalClick(item.href)}
                            className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-primary text-left"
                          >
                            <ExternalLink className="h-3 w-3 shrink-0" />
                            <span className="truncate">{item.label}</span>
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{item.tooltip}</p>
                        </TooltipContent>
                      </Tooltip>
                    </li>
                  )
                })}
              </ul>
            </TooltipProvider>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-12 border-t border-border pt-8">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <p className="text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} ForestGuard Argentina. {t('footerCopyright')}
            </p>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span>{t('footerMadeWith')}</span>
              <span className="text-destructive">❤</span>
              <span>{t('footerProtectForests')}</span>
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={!!pendingHref} onOpenChange={cancelNavigation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              {t('footerLeavingTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('footerLeavingDescription')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelNavigation}>{t('footerCancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmNavigation}>{t('footerContinue')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </footer>
  )
}
