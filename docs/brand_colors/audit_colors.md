# Auditoría de Colores Actuales

Este documento registra las variables de color CSS globales (`index.css`) utilizadas en el sistema de diseño actual. Todas las variables se definen en formato HSL sin la función CSS, ya que Tailwind las inyecta en su configuración con `hsl(var(--nombre))`.

## Modo Claro (`:root`)

| Variable | Valor HSL | Uso típico en Tailwind (`bg-`, `text-`, `border-`) |
|----------|-----------|-----------------------------------------------------|
| `--background` | `0 0% 98%` | Fondo principal de la aplicación. |
| `--foreground` | `40 10% 20%` | Texto principal. |
| `--card` | `0 0% 100%` | Fondo de las tarjetas. |
| `--card-foreground` | `40 10% 20%` | Texto dentro de tarjetas. |
| `--popover` | `0 0% 100%` | Fondo de *tooltips*, modales y popovers. |
| `--popover-foreground` | `40 10% 20%` | Texto dentro de popovers. |
| `--primary` | `155 55% 45%` | Color principal para elementos destacados (botones, links). |
| `--primary-foreground` | `0 0% 100%` | Texto dentro de elementos primarios. |
| `--secondary` | `40 20% 35%` | Color secundario. |
| `--secondary-foreground` | `0 0% 100%` | Texto dentro de elementos secundarios. |
| `--muted` | `100 10% 95%` | Fondos de elementos silenciados o secundarios inactivos. |
| `--muted-foreground` | `40 10% 40%` | Texto atenuado/mutado. |
| `--accent` | `40 60% 70%` | Color de acento (estados hover de items de navegación). |
| `--accent-foreground` | `40 10% 25%` | Texto dentro de color de acento. |
| `--destructive` | `0 84% 60%` | Acciones destructivas (errores, alertas graves). |
| `--destructive-foreground` | `0 0% 100%` | Texto de acciones destructivas. |
| `--border` | `110 10% 88%` | Bordes regulares de elementos (inputs, divisores). |
| `--input` | `110 10% 92%` | Bordes/Fondos de inputs de formularios. |
| `--ring` | `155 55% 45%` | Color de aro enfocado (`focus:ring`). |

### Gráficos / Charts
- `--chart-1`: `155 55% 45%`
- `--chart-2`: `40 20% 35%`
- `--chart-3`: `0 84% 60%`
- `--chart-4`: `40 70% 70%`
- `--chart-5`: `20 70% 55%`

### Sidebar
- `--sidebar`: `100 10% 98%`
- `--sidebar-foreground`: `40 10% 20%`
- `--sidebar-primary`: `155 55% 45%`
- `--sidebar-primary-foreground`: `0 0% 100%`
- `--sidebar-accent`: `110 10% 92%`
- `--sidebar-accent-foreground`: `40 10% 25%`
- `--sidebar-border`: `110 10% 88%`
- `--sidebar-ring`: `155 55% 45%`


## Modo Oscuro (`.dark`)

| Variable | Valor HSL |
|----------|-----------|
| `--background` | `40 10% 18%` |
| `--foreground` | `100 10% 95%` |
| `--card` | `40 10% 22%` |
| `--card-foreground` | `100 10% 95%` |
| `--popover` | `40 10% 22%` |
| `--popover-foreground` | `100 10% 95%` |
| `--primary` | `155 55% 45%` |
| `--primary-foreground` | `40 10% 15%` |
| `--secondary` | `40 25% 45%` |
| `--secondary-foreground` | `100 10% 95%` |
| `--muted` | `40 10% 28%` |
| `--muted-foreground` | `100 10% 65%` |
| `--accent` | `40 40% 45%` |
| `--accent-foreground` | `100 10% 95%` |
| `--destructive` | `0 65% 50%` |
| `--destructive-foreground` | `100 10% 95%` |
| `--border` | `40 10% 32%` |
| `--input` | `40 10% 28%` |
| `--ring` | `155 55% 45%` |

### Gráficos / Charts
- `--chart-1`: `155 55% 45%`
- `--chart-2`: `40 25% 45%`
- `--chart-3`: `0 65% 50%`
- `--chart-4`: `40 55% 70%`
- `--chart-5`: `20 70% 65%`

### Sidebar
- `--sidebar`: `40 10% 20%`
- `--sidebar-foreground`: `100 10% 95%`
- `--sidebar-primary`: `155 55% 45%`
- `--sidebar-primary-foreground`: `40 10% 15%`
- `--sidebar-accent`: `40 10% 28%`
- `--sidebar-accent-foreground`: `100 10% 95%`
- `--sidebar-border`: `40 10% 32%`
- `--sidebar-ring`: `155 55% 45%`
