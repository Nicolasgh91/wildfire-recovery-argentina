import { Link } from 'react-router-dom'
import { Trees, Map, ClipboardCheck, FileText, HelpCircle, BookOpen, GraduationCap, Mail, ExternalLink } from 'lucide-react'

export function Footer() {
  const productLinks = [
    { href: '/', label: 'Mapa de Incendios', icon: Map },
    { href: '/audit', label: 'Auditoría Legal', icon: ClipboardCheck },
    { href: '/exploracion', label: 'Exploraci\u00f3n satelital', icon: FileText },
    { href: '/citizen-report', label: 'Reporte Ciudadano', icon: FileText },
  ]

  const supportLinks = [
    { href: '/faq', label: 'Preguntas Frecuentes', icon: HelpCircle },
    { href: '/manual', label: 'Manual de Usuario', icon: BookOpen },
    { href: '/glossary', label: 'Glosario', icon: GraduationCap },
  ]

  const companyLinks = [
    { href: '/contact', label: 'Contacto', icon: Mail },
    { href: 'https://forestguard.freedynamicdns.org/docs', label: 'API Docs', icon: ExternalLink, external: true },
  ]

  return (
    <footer className="hidden md:block border-t border-border bg-card">
      <div className="container mx-auto px-6 py-12">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Trees className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold text-foreground">ForestGuard</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Plataforma de monitoreo y recuperación de incendios forestales de Argentina.
              Protegemos nuestros bosques con tecnología satelital.
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
              Compañía
            </h3>
            <ul className="flex flex-col gap-3">
              {companyLinks.map((link) => (
                <li key={link.href}>
                  {'external' in link && link.external ? (
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
    </footer>
  )
}
