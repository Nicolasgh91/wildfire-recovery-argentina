import { useEffect, useMemo, useState } from 'react'
import { KeyRound, Mail } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  RESET_PASSWORD_NEUTRAL_MESSAGE,
  useAccountActions,
} from '@/features/account/hooks/use-account-actions'

const RESET_COOLDOWN_SECONDS = 30

export function PasswordSecurityCard() {
  const { isOAuthUser, updatePassword, sendPasswordReset } = useAccountActions()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false)
  const [isSendingReset, setIsSendingReset] = useState(false)
  const [cooldownSeconds, setCooldownSeconds] = useState(0)

  const canSubmitPassword = useMemo(() => {
    if (!isOAuthUser && currentPassword.length === 0) return false
    if (newPassword.length < 8) return false
    return newPassword === confirmPassword
  }, [confirmPassword, currentPassword.length, isOAuthUser, newPassword])

  useEffect(() => {
    if (cooldownSeconds <= 0) return
    const timer = window.setInterval(() => {
      setCooldownSeconds((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)

    return () => window.clearInterval(timer)
  }, [cooldownSeconds])

  const handleUpdatePassword = async () => {
    if (!canSubmitPassword) {
      toast.error('Revisa los campos de seguridad antes de continuar.')
      return
    }

    setIsUpdatingPassword(true)
    try {
      await updatePassword({
        currentPassword: isOAuthUser ? undefined : currentPassword,
        newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      toast.success('Contrasena actualizada correctamente.')
    } catch {
      toast.error('No se pudo actualizar la contrasena. Verifica tu sesion e intenta nuevamente.')
    } finally {
      setIsUpdatingPassword(false)
    }
  }

  const handleSendReset = async () => {
    if (cooldownSeconds > 0) return
    setIsSendingReset(true)
    try {
      await sendPasswordReset()
      toast.success(RESET_PASSWORD_NEUTRAL_MESSAGE)
      setCooldownSeconds(RESET_COOLDOWN_SECONDS)
    } catch {
      toast.error('No se pudo iniciar el reseteo en este momento.')
    } finally {
      setIsSendingReset(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          Seguridad de cuenta
        </CardTitle>
        <CardDescription>
          Cambia tu contrasena con reautenticacion previa. Para reset por correo usamos mensaje neutro anti-enumeracion.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isOAuthUser && (
          <div className="space-y-2">
            <Label htmlFor="current-password">Contrasena actual</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="new-password">Nueva contrasena</Label>
          <Input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">Minimo 8 caracteres.</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm-password">Confirmar nueva contrasena</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            type="button"
            onClick={() => void handleUpdatePassword()}
            disabled={!canSubmitPassword || isUpdatingPassword}
          >
            {isUpdatingPassword ? 'Actualizando...' : 'Actualizar contrasena'}
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={() => void handleSendReset()}
            disabled={isSendingReset || cooldownSeconds > 0}
          >
            <Mail className="mr-2 h-4 w-4" />
            {cooldownSeconds > 0
              ? `Reintentar en ${cooldownSeconds}s`
              : isSendingReset
                ? 'Enviando...'
                : 'Enviar email de reset'}
          </Button>
        </div>

        {isOAuthUser && (
          <p className="text-xs text-muted-foreground">
            Esta cuenta usa proveedor OAuth. Usa reset por correo para definir una contrasena local si aplica.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
