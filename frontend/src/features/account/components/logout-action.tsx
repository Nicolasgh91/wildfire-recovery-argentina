import { useState } from 'react'
import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAccountActions } from '@/features/account/hooks/use-account-actions'
import { LOGIN_PATH } from '@/lib/routing'

interface LogoutActionProps {
  className?: string
  onAfterLogout?: () => void
}

export function LogoutAction({ className, onAfterLogout }: LogoutActionProps) {
  const { logout } = useAccountActions()
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const handleLogout = async () => {
    setIsLoading(true)
    try {
      await logout()
      onAfterLogout?.()
      navigate(LOGIN_PATH)
    } catch {
      toast.error('No se pudo cerrar la sesion.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Button
      type="button"
      variant="destructive"
      className={className}
      onClick={() => void handleLogout()}
      disabled={isLoading}
    >
      <LogOut className="mr-2 h-4 w-4" />
      {isLoading ? 'Cerrando sesion...' : 'Cerrar sesion'}
    </Button>
  )
}
