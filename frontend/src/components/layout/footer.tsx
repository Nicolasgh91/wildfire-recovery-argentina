import { Link } from 'react-router-dom'
import { Trees } from 'lucide-react'
import { useI18n } from '@/context/LanguageContext'

export function Footer() {
  const { t } = useI18n()

  return (
    <footer className="hidden md:block border-t border-border bg-card py-8">
      <div className="container mx-auto px-6">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2">
            <Trees className="h-6 w-6 text-primary" />
            <span className="font-semibold text-foreground">ForestGuard</span>
          </div>
          
          <nav className="flex items-center gap-6 text-sm">
            <Link to="/legal" className="text-muted-foreground transition-colors hover:text-foreground">
              {t('legal')}
            </Link>
            <Link to="/contact" className="text-muted-foreground transition-colors hover:text-foreground">
              {t('contact')}
            </Link>
            <a 
              href="https://forestguard.freedynamicdns.org/docs" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              {t('apiDocs')}
            </a>
          </nav>

          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} ForestGuard Argentina
          </p>
        </div>
      </div>
    </footer>
  )
}
