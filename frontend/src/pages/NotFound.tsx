import { Link } from 'react-router-dom'
import { AlertTriangle, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto flex max-w-xl items-center justify-center px-4 py-20">
        <Card className="w-full border-border bg-card">
          <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="h-7 w-7 text-destructive" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Page not found</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                The page you are looking for does not exist or was moved.
              </p>
            </div>
            <Button asChild className="gap-2">
              <Link to="/">
                <Home className="h-4 w-4" />
                Back to home
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
