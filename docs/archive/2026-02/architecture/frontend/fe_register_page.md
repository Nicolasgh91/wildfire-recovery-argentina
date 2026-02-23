# FE-REG-01: Pagina de registro (UI + flujo email)

**Fecha**: 2026-02-05  
**Owner**: Frontend  
**Estado**: Pendiente

## Objetivo
Implementar la pagina de registro con el mismo layout que la landing de login, capturando nombre, apellido y email, y registrando al usuario en la tabla designada.

## Alcance
- Frontend: nueva ruta `/register` con layout identico a `/login`.
- Registro via email (passwordless) usando Supabase Auth.
- Persistencia: guardar nombre/apellido en metadata y asegurar alta en tabla `users` local.
- No incluye cambios visuales en otras paginas.

## Supuestos a validar
1. **Tabla destino**: se considera `users` (backend) y se crea/actualiza via `get_or_create_supabase_user` cuando el usuario inicia sesion con JWT de Supabase.
2. **Registro sin password**: se usa email OTP (magic link) para respetar el requisito de solo nombre, apellido y email.
3. **Google en registro**: se mantiene el boton de Google en la pagina de registro (opcional) para consistencia con login.

> Si alguno de estos supuestos no aplica, ajustar el flujo antes de implementar.

## Requisitos / Inputs
- Supabase Auth habilitado (email OTP y Google si aplica).
- Variables:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_USE_SUPABASE_JWT=true`

## UX / Layout
- Mismo layout que `/login` (grid 50/50 en desktop, imagen oculta en mobile).
- Bloque de registro centrado, max-width 360–420px, texto centrado.
- Logo en esquina superior izquierda (mismo que login).
- Campos:
  - Nombre (required)
  - Apellido (required)
  - Email (required, formato valido)
- Boton primario: “Registrarme con email”.
- Separador + CTA “Continuar como invitado”.
- Link a login: “Ya tenes cuenta? Iniciar sesion”.

## Validaciones
- Nombre: requerido, min 2, max 50.
- Apellido: requerido, min 2, max 50.
- Email: requerido, formato valido.
- Mostrar errores inline (Input + mensaje).

## Implementacion tecnica

### 1) Ruta /register
- Agregar pagina `frontend/src/pages/Register.tsx`.
- En `App.tsx`, agregar ruta `/register`.

### 2) Formulario
- Usar `react-hook-form` + `zod` (mismo stack del proyecto).
- Schema:
```ts
const registerSchema = z.object({
  first_name: z.string().min(2).max(50),
  last_name: z.string().min(2).max(50),
  email: z.string().email(),
})
```

### 3) Supabase Auth (passwordless)
- En `AuthContext`, agregar metodo:
```ts
const signUpWithEmail = async (payload: { email: string; firstName: string; lastName: string }) => {
  const { error } = await supabase.auth.signInWithOtp({
    email: payload.email,
    options: {
      data: {
        full_name: `${payload.firstName} ${payload.lastName}`.trim(),
        first_name: payload.firstName,
        last_name: payload.lastName,
      },
      emailRedirectTo: window.location.origin,
    },
  })
  if (error) throw error
}
```

### 4) Persistencia en tabla `users`
- Al finalizar login (cuando exista JWT), llamar `GET /auth/me` para forzar `get_or_create_supabase_user` y persistir el usuario local.
- Confirmar que `user_metadata.full_name` se guarda en `auth.users` y se refleja en `users.full_name`.

### 5) Mensajes de estado
- Mostrar confirmacion: “Te enviamos un link a tu email para finalizar el registro”.
- Manejar errores de Supabase (rate limit, email invalid, etc).

## Tests
### Manual
1. Abrir `/register`.
2. Completar nombre/apellido/email.
3. Recibir email OTP y completar login.
4. Verificar sesion activa y que `GET /auth/me` responde OK.
5. Verificar registro en tabla `users`.

### Unit (opcional)
- Mock de `supabase.auth.signInWithOtp` y validacion de payload.

## Criterios de aceptacion
- Pagina `/register` replica el layout del login.
- Validaciones funcionan y muestran errores.
- Se envia OTP y el usuario puede autenticarse.
- El usuario queda registrado en `users` con `full_name` correcto.

## Pendientes
- Confirmar si la tabla destino es `users` (backend) o una tabla de perfiles distinta.
- Confirmar si se mantiene boton Google en registro.
