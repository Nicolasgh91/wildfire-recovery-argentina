# Prompt para implementar opciones de registro en Supabase

Eres un agente de código experto en integraciones frontend y backend. Tu tarea es construir un sistema de autenticación robusto utilizando el cliente de Supabase, implementando tres métodos simultáneos: OTP, correo con contraseña y OAuth de Google.

## Tareas técnicas
1. Instanciar el cliente de Supabase y configurar los manejadores de eventos de estado de sesión (`onAuthStateChange`).
2. Desarrollar formularios controlados para cada método de autenticación.
3. Implementar un sistema de notificaciones en la interfaz (toasts o alertas) para gestionar la retroalimentación al usuario.
4. Configurar el enrutamiento para proteger vistas privadas y gestionar redirecciones tras el login exitoso.

## Opción 1: OTP (enlace mágico)
* **Campos a renderizar:** Entrada de texto para correo electrónico y botón principal de envío.
* **Validaciones:** Expresión regular para formato de correo electrónico válido; evitar envíos con el campo vacío.
* **Mensajes de error:**
  * "Ingresa una dirección de correo válida."
  * "Demasiados intentos. Espera 60 segundos antes de solicitar un nuevo enlace." (Error 429).
* **Mensajes de éxito:**
  * "Revisa tu bandeja de entrada. Hemos enviado un enlace de acceso a [correo]."
* **UX adicional:** Ocultar el formulario tras el envío exitoso y mostrar un botón de reenvío deshabilitado con un temporizador de 60 segundos.

## Opción 2: Correo y contraseña
* **Campos a renderizar (registro):** Correo electrónico, contraseña, confirmar contraseña, indicador de fortaleza de contraseña, botón de registro.
* **Campos a renderizar (login):** Correo electrónico, contraseña, botón de ingreso, enlace a recuperación de contraseña.
* **Validaciones:** Longitud de contraseña mayor a 8 caracteres, validación cruzada entre contraseña y confirmación.
* **Mensajes de error:**
  * "Las contraseñas no coinciden."
  * "La contraseña es demasiado débil."
  * "Credenciales incorrectas. Verifica tu correo y contraseña." (Para login).
  * "El usuario ya existe." (Para registro).
* **Mensajes de éxito:**
  * "Cuenta creada. Redirigiendo al panel..."
  * "Bienvenido de nuevo."

## Opción 3: OAuth (Google)
* **Campos a renderizar:** Botón único con icono de Google y el texto "Continuar con Google".
* **Validaciones:** Capturar la promesa devuelta por `signInWithOAuth` para detectar bloqueos de ventanas emergentes o cancelaciones del usuario.
* **Mensajes de error:**
  * "No se pudo completar la autenticación con Google. Intenta de nuevo."
* **Mensajes informativos:** Deshabilitar toda la interfaz de login y mostrar un indicador de carga centralizado mientras ocurre la redirección al proveedor.

## Regresiones a testear
1. **Persistencia de sesión:** Comprobar que al refrescar el navegador (F5), la sesión se recupere automáticamente desde el almacenamiento local sin pedir credenciales.
2. **Colisión de proveedores:** Iniciar sesión con Google, cerrar sesión e intentar registrar una cuenta con contraseña usando el mismo correo de Gmail. Verificar la respuesta de Supabase y el manejo del error en la interfaz.
3. **Estados de carga concurrentes:** Validar que al hacer clic en el botón de Google, los campos y botones de OTP y contraseña se deshabiliten para prevenir mutaciones paralelas.
4. **Ciclo de vida del magic link:** Solicitar un enlace OTP, esperar su expiración, hacer clic en él y verificar que la interfaz capture y muestre el error de token expirado de forma amigable, ofreciendo solicitar uno nuevo.
5. **Redirección de rutas:** Acceder a una ruta protegida mediante la barra de direcciones sin sesión activa, comprobar el redireccionamiento al login y, tras el inicio de sesión, verificar que el usuario sea devuelto a la ruta original solicitada.