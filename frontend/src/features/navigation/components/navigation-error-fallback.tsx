import { Home, LogIn, LogOut, Map as MapIcon, TriangleAlert } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'
import { HOME_PATH, LOGIN_PATH } from '@/lib/routing'

export function NavigationErrorFallback() {
  const navigate = useNavigate()
  const { isAuthenticated, signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
    navigate(LOGIN_PATH)
  }

  return (
    <div className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <TriangleAlert className="h-4 w-4 text-yellow-500" />
          <span>Hubo un error en la navegacion. Usa accesos rapidos.</span>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline">
            <Link to={HOME_PATH}>
              <Home className="h-4 w-4" />
              Inicio
            </Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to="/map">
              <MapIcon className="h-4 w-4" />
              Mapa
            </Link>
          </Button>
          {isAuthenticated ? (
            <Button size="sm" variant="default" onClick={() => void handleSignOut()}>
              <LogOut className="h-4 w-4" />
              Cerrar sesion
            </Button>
          ) : (
            <Button asChild size="sm" variant="default">
              <Link to={LOGIN_PATH}>
                <LogIn className="h-4 w-4" />
                Iniciar sesion
              </Link>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
