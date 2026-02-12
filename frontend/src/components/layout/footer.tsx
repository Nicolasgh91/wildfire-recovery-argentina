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

export function Footer() {
  const [pendingHref, setPendingHref] = React.useState<string | null>(null)

  const productLinks = [
    { href: '/fires/history', label: 'Históricos', icon: HistoryIcon },
    { href: '/map', label: 'Mapa de Incendios', icon: Map },
    { href: '/audit', label: 'Verificar terreno', icon: ClipboardCheck },
    { href: '/exploracion', label: 'Exploración satelital', icon: FileText },
  ]

  const supportLinks = [
    { href: '/faq', label: 'Preguntas Frecuentes', icon: HelpCircle },
    { href: '/manual', label: 'Manual de Usuario', icon: BookOpen },
    { href: '/glossary', label: 'Glosario', icon: GraduationCap },
  ]

  const companyLinks = [
    { href: '/contact', label: 'Contacto', icon: Mail },
    { href: 'https://forestguard.freedynamicdns.org/docs', label: 'API Docs', icon: ExternalLink, external: true },
    { href: 'https://www.argentina.gob.ar/parquesnacionales', label: 'Parques Nacionales', icon: ExternalLink, external: true, tooltip: "Información sobre áreas protegidas nacionales." },
    { href: 'https://www.argentina.gob.ar/reporte-diario-de-incendios', label: 'Reporte diario de incendios', icon: ExternalLink, external: true, tooltip: "Informes diarios de estado de situación de incendios." },
  ]

  const PUBLIC_SOURCES_AR = [
    { label: "Servicio Nacional de Manejo del Fuego", href: "https://www.argentina.gob.ar/servicio-nacional-de-manejo-del-fuego", tooltip: "Sitio oficial del SNMF con información sobre incendios en Argentina." },
    [
      { label: "Boletín Oficial", href: "https://www.boletinoficial.gob.ar/", tooltip: "Normativas y publicaciones oficiales de la República Argentina." },
      { label: "CONAE", href: "https://catalogos5.conae.gov.ar/catalogofocos/", tooltip: "Catálogo de focos de calor y áreas quemadas por satélite." },
    ],
    { label: "Servicio Meteorológico Nacional", href: "https://ws2.smn.gob.ar/", tooltip: "Pronósticos y alertas meteorológicas oficiales." },
    [
      { label: "SPMF Chubut", href: "https://bosques.chubut.gov.ar/manejo-del-fuego/", tooltip: "Servicio de Prevención y Lucha contra Incendios Forestales de Chubut." },
      { label: "SPLIF Río Negro", href: "https://splif.rionegro.gov.ar/", tooltip: "Servicio de Prevención y Lucha contra Incendios Forestales de Río Negro." },
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
              Plataforma de monitoreo y recuperación de incendios forestales de Argentina.
              Protegemos nuestros bosques entre todos.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-foreground">
              Producto
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
              Soporte
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
              INFORMATIVOS
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
              FUENTES PÚBLICAS
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
              &copy; {new Date().getFullYear()} ForestGuard Argentina. Todos los derechos reservados.
            </p>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <span>Hecho con</span>
              <span className="text-destructive">❤</span>
              <span>para proteger nuestros bosques</span>
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={!!pendingHref} onOpenChange={cancelNavigation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Estás saliendo de ForestGuard
            </AlertDialogTitle>
            <AlertDialogDescription>
              Vas a ser redirigido a un sitio externo oficial.
              El contenido de este sitio no depende de nosotros.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelNavigation}>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmNavigation}>Continuar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </footer>
  )
}
