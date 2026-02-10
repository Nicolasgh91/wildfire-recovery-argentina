import { AlertCircle, Mail } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { ContactForm } from '@/components/contact/ContactForm'

export default function ContactPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-primary/10 p-3">
            <Mail className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">Contacto</h1>
          <p className="mt-2 text-muted-foreground">
            ¿Tienes preguntas o comentarios? Estamos aquí para ayudarte.
          </p>
        </div>

        <ContactForm />

        <Card className="mt-6 bg-muted/50">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 h-5 w-5 text-muted-foreground" />
            <div className="text-sm text-muted-foreground">
              <p>
                Para consultas urgentes relacionadas con incendios activos, por favor contacte
                directamente al <strong>Sistema Nacional de Manejo del Fuego</strong> al teléfono{' '}
                <strong>0800-222-4825</strong>.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
