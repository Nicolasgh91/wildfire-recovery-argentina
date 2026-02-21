# Addendum de Cierre — 3 Gaps Residuales

## Resumen
Se aprueba el plan previo con 3 ajustes obligatorios para eliminar ambigüedad técnica y dejar implementación decision-complete.

## Cambios de interfaces/tipos
1. Navegación:
- En `frontend/src/features/navigation/config/navigation.ts` se agrega `activeMatch: 'exact' | 'prefix'` por item.
- Regla de render: `NavLink` usa `end={activeMatch === 'exact'}`.
- Regla de uso: rutas con hijos dinámicos usan `prefix`; rutas hoja usan `exact`.

2. Fallback de navegación:
- `frontend/src/features/navigation/components/navigation-error-fallback.tsx` debe exponer acciones funcionales mínimas:
- Link a `/home`.
- Link a `/map`.
- Acción de cuenta: `logout` si autenticado, `login` si no autenticado.

3. Delete account / FK citizen reports:
- En PR5 se fuerza política de preservación de evidencia:
- `citizen_reports.reporter_user_id` debe quedar con FK `REFERENCES users(id) ON DELETE SET NULL`.
- Si el constraint existe con otra política, se reemplaza.
- Si no existe, se crea.
- Si no puede aplicarse, PR5 no mergea (falla de migración/test).
- Resultado funcional: reportes ciudadanos se preservan y el vínculo de usuario se nulifica/anonimiza.

## Ajustes al plan por PR
1. PR1:
- Incluir `activeMatch` en configuración y tests de active state para rutas con y sin segmentos dinámicos.

2. PR5:
- Migración `account_delete_fk_alignment.sql` deja de ser “opcional ambigua” y pasa a ser enforcement obligatorio para `citizen_reports.reporter_user_id`.
- Añadir test de integración backend que verifique:
- Borrado lógico de usuario.
- `citizen_reports.reporter_user_id` en `NULL` para registros vinculados.
- Reporte ciudadano preservado.

3. PR0/PR2 (fallback):
- `navigation-error-fallback.tsx` se define como fallback operativo, no informativo-only.

## Tests y escenarios mínimos
1. Navegación:
- Ruta padre con `prefix` permanece activa en subrutas dinámicas.
- Ruta `exact` no queda activa fuera de su path exacto.

2. Error fallback:
- Simular error en drawer/nav y verificar que `/home` y `/map` siguen accesibles.
- Verificar acción auth-aware (`logout` vs `login`).

3. Delete account:
- Ejecutar eliminación de cuenta y verificar `citizen_reports` preservado con `reporter_user_id = NULL`.
- Verificar bloqueo de acceso posterior del usuario eliminado.

## Supuestos y defaults
- Preservación de evidencia es prioritaria sobre hard delete.
- No se introducen nuevas librerías.
- Si el esquema real difiere, la política objetivo no cambia: preservar `citizen_reports` y nulificar vínculo de usuario.
