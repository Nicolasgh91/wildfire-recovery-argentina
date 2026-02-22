import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LOGIN_PATH } from '@/lib/routing'
import { useAuth } from '@/context/AuthContext'
import { useAccountActions } from '@/features/account/hooks/use-account-actions'

const DELETE_CONFIRM_TEXT = 'ELIMINAR'

export function DeleteAccountDialog() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { isOAuthUser, requestDeleteChallenge, deleteAccount, logout } = useAccountActions()

  const [open, setOpen] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [password, setPassword] = useState('')
  const [challengeToken, setChallengeToken] = useState('')
  const [isRequestingChallenge, setIsRequestingChallenge] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const canDelete = confirmText === DELETE_CONFIRM_TEXT && (
    isOAuthUser ? challengeToken.trim().length > 0 : password.trim().length > 0
  )

  const resetDialogState = () => {
    setConfirmText('')
    setPassword('')
    setChallengeToken('')
  }

  const handleRequestChallenge = async () => {
    setIsRequestingChallenge(true)
    try {
      await requestDeleteChallenge()
      toast.success('Se envio un token temporal al correo de la cuenta.')
    } catch {
      toast.error('No se pudo generar el challenge de eliminacion.')
    } finally {
      setIsRequestingChallenge(false)
    }
  }

  const handleDelete = async () => {
    if (!canDelete) return

    setIsDeleting(true)
    try {
      await deleteAccount({
        confirmationText: confirmText,
        password: isOAuthUser ? undefined : password,
        challengeToken: isOAuthUser ? challengeToken : undefined,
        reason: 'user_request',
      })
      await logout()
      setOpen(false)
      resetDialogState()
      toast.success('Tu cuenta fue eliminada.')
      navigate(LOGIN_PATH, { replace: true })
    } catch {
      toast.error('No se pudo eliminar la cuenta. Revisa los datos y vuelve a intentar.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (!nextOpen) resetDialogState()
      }}
    >
      <AlertDialogTrigger asChild>
        <Button type="button" variant="destructive">
          Eliminar cuenta
        </Button>
      </AlertDialogTrigger>

      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Esta accion es irreversible
          </AlertDialogTitle>
          <AlertDialogDescription>
            Escribe <strong>{DELETE_CONFIRM_TEXT}</strong> para continuar. Los reportes ciudadanos se conservan y se anonimiza el vinculo del usuario.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="delete-confirmation-text">Confirmacion</Label>
            <Input
              id="delete-confirmation-text"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              placeholder={DELETE_CONFIRM_TEXT}
            />
          </div>

          {isOAuthUser ? (
            <>
              <div className="space-y-2">
                <Label>Cuenta OAuth detectada</Label>
                <p className="text-xs text-muted-foreground">
                  Solicitamos un token temporal por email para confirmar eliminacion de {user?.email ?? 'la cuenta actual'}.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleRequestChallenge()}
                  disabled={isRequestingChallenge}
                >
                  {isRequestingChallenge ? 'Enviando token...' : 'Enviar token por email'}
                </Button>
                <Input
                  value={challengeToken}
                  onChange={(event) => setChallengeToken(event.target.value)}
                  placeholder="Token de verificacion"
                />
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="delete-password">Contrasena actual</Label>
              <Input
                id="delete-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            onClick={(event) => {
              event.preventDefault()
              void handleDelete()
            }}
            disabled={!canDelete || isDeleting}
          >
            {isDeleting ? 'Eliminando...' : 'Confirmar eliminacion'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
