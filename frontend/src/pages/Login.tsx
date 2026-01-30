import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Trees, LogIn, AlertCircle, Globe, Sun, Moon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useI18n } from '@/context/LanguageContext'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from 'next-themes'

export default function LoginPage() {
  const navigate = useNavigate()
  const { t, language, setLanguage } = useI18n()
  const { login } = useAuth()
  const { theme, setTheme } = useTheme()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError(t('loginError'))
      return
    }

    setIsLoading(true)

    await new Promise((resolve) => setTimeout(resolve, 800))

    const success = login(email, password)

    if (success) {
      navigate('/')
    } else {
      setError(t('loginError'))
    }

    setIsLoading(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-primary/5 to-background p-4">
      <div className="fixed right-4 top-4 flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <Globe className="h-5 w-5" />
              <span className="sr-only">Toggle language</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setLanguage('es')}>
              <span className={language === 'es' ? 'font-bold' : ''}>Español</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setLanguage('en')}>
              <span className={language === 'en' ? 'font-bold' : ''}>English</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </div>

      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Trees className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">ForestGuard</CardTitle>
          <CardDescription>{t('login')} to access all features</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">{t('email')}</Label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                type="password"
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            <Button type="submit" className="w-full gap-2" disabled={isLoading}>
              {isLoading ? (
                'Loading...'
              ) : (
                <>
                  <LogIn className="h-4 w-4" />
                  {t('loginButton')}
                </>
              )}
            </Button>
          </form>

          <div className="mt-4 rounded-lg border border-border bg-muted/50 p-3 text-xs text-muted-foreground">
            <p className="mb-1 font-medium">Demo Accounts:</p>
            <p>- Any email: Regular User</p>
            <p>- admin@forestguard.ar: Administrator</p>
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-2 text-center text-sm text-muted-foreground">
          <p>
            {t('noAccount')}{' '}
            <Link to="/" className="text-primary underline">
              {t('register')}
            </Link>
          </p>
          <Link to="/" className="text-primary underline">
            Continue as {t('guest')}
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
