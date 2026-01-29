# 🎨 Wildfire Recoveries in Argentina - Guía de Branding

## Paleta de colores oficial

### Colores primarios

| Color | Hex | RGB | Uso Típico |
|-------|-----|-----|------------|
| **Naranja Fuego** | `#F66A23` | `rgb(246, 106, 35)` | Incendios activos, alertas, puntos de calor en mapa |
| **Rojo Intenso** | `#D93725` | `rgb(217, 55, 37)` | Riesgo alto, prohibiciones, estados críticos |
| **Verde Oscuro** | `#4F9F4A` | `rgb(79, 159, 74)` | Áreas protegidas, vegetación saludable |
| **Verde Claro** | `#A8D875` | `rgb(168, 216, 117)` | Recuperación de vegetación, NDVI alto |

### Colores neutros

| Color | Hex | RGB | Uso Típico |
|-------|-----|-----|------------|
| **Gris Oscuro** | `#323232` | `rgb(50, 50, 50)` | Texto principal, fondos oscuros |
| **Gris Claro** | `#E0E0E0` | `rgb(224, 224, 224)` | Texto secundario, líneas divisorias, fondos claros |

### Colores derivados (para UI)

```css
/* Variantes calculadas para hover states, etc */
--fire-orange-dark: #E45A13;    /* Naranja -10% brillo */
--fire-orange-light: #F88A53;   /* Naranja +10% brillo */

--danger-red-dark: #C92715;     /* Rojo -10% brillo */
--danger-red-light: #E34735;    /* Rojo +10% brillo */

--success-green-dark: #3F8F3A;  /* Verde oscuro -10% */
--success-green-light: #5FAF5A; /* Verde oscuro +10% */

--recovery-green-dark: #98C865; /* Verde claro -10% */
--recovery-green-light: #B8E085; /* Verde claro +10% */
```

---

## 📁 Estructura de assets

```
frontend/public/assets/
├── logos/
│   ├── logo-horizontal.svg       # Logo principal (para headers)
│   ├── logo-horizontal.png       # Fallback PNG
│   ├── logo-horizontal-white.svg # Versión para fondos oscuros
│   ├── logo-icon.svg             # Solo ícono (favicon)
│   └── logo-icon.png             # 512x512px
│
├── favicon/
│   ├── favicon.ico               # 16x16, 32x32, 48x48
│   ├── favicon-16x16.png
│   ├── favicon-32x32.png
│   └── apple-touch-icon.png      # 180x180px
│
└── og/
    └── og-image.png              # 1200x630px para redes sociales
```

---

## 🎨 Aplicación en componentes

### 1. PDFs (certificados y reportes judiciales)

```python
# app/services/pdf_service.py

from weasyprint import HTML, CSS
from jinja2 import Template

class PDFService:
    
    COLORS = {
        'primary': '#F66A23',       # Naranja fuego
        'danger': '#D93725',        # Rojo intenso
        'success': '#4F9F4A',       # Verde oscuro
        'recovery': '#A8D875',      # Verde claro
        'text_dark': '#323232',     # Gris oscuro
        'text_light': '#E0E0E0',    # Gris claro
        'white': '#FFFFFF'
    }
    
    CERTIFICATE_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Helvetica', 'Arial', sans-serif;
                color: {{ colors.text_dark }};
                line-height: 1.6;
            }
            
            /* Header con degradado */
            .header {
                background: linear-gradient(135deg, {{ colors.primary }} 0%, {{ colors.danger }} 100%);
                padding: 30px;
                color: {{ colors.white }};
                border-radius: 8px;
                margin-bottom: 30px;
                text-align: center;
            }
            
            .logo-container {
                margin-bottom: 20px;
            }
            
            .logo {
                max-width: 300px;
                height: auto;
            }
            
            .header h1 {
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
            }
            
            .header h2 {
                font-size: 18px;
                font-weight: 400;
                opacity: 0.9;
            }
            
            /* Certificate number badge */
            .cert-number {
                background: {{ colors.white }};
                color: {{ colors.primary }};
                padding: 10px 20px;
                border-radius: 20px;
                font-weight: 700;
                font-size: 14px;
                display: inline-block;
                margin-top: 15px;
            }
            
            /* Status badges */
            .status-badge {
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: 700;
                font-size: 16px;
                text-align: center;
                margin: 20px 0;
            }
            
            .status-clear {
                background-color: {{ colors.success }};
                color: {{ colors.white }};
                border-left: 6px solid {{ colors.recovery }};
            }
            
            .status-prohibited {
                background-color: {{ colors.danger }};
                color: {{ colors.white }};
                border-left: 6px solid {{ colors.primary }};
            }
            
            .status-restricted {
                background-color: {{ colors.primary }};
                color: {{ colors.white }};
                border-left: 6px solid {{ colors.danger }};
            }
            
            /* Content sections */
            .section {
                margin-bottom: 30px;
            }
            
            .section-title {
                font-size: 18px;
                font-weight: 700;
                color: {{ colors.primary }};
                border-bottom: 2px solid {{ colors.text_light }};
                padding-bottom: 8px;
                margin-bottom: 15px;
            }
            
            .info-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            
            .info-item {
                padding: 10px;
                background: #FAFAFA;
                border-left: 3px solid {{ colors.primary }};
            }
            
            .info-label {
                font-size: 12px;
                color: {{ colors.text_light }};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
            
            .info-value {
                font-size: 16px;
                font-weight: 600;
                color: {{ colors.text_dark }};
            }
            
            /* Fire events table */
            .fire-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            
            .fire-table th {
                background: {{ colors.text_dark }};
                color: {{ colors.white }};
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
            }
            
            .fire-table td {
                padding: 10px 12px;
                border-bottom: 1px solid {{ colors.text_light }};
                font-size: 13px;
            }
            
            .fire-table tr:nth-child(even) {
                background: #F9F9F9;
            }
            
            .fire-intensity {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
            }
            
            .intensity-high {
                background: {{ colors.danger }};
                color: {{ colors.white }};
            }
            
            .intensity-medium {
                background: {{ colors.primary }};
                color: {{ colors.white }};
            }
            
            .intensity-low {
                background: {{ colors.recovery }};
                color: {{ colors.text_dark }};
            }
            
            /* Footer with verification */
            .footer {
                margin-top: 50px;
                padding-top: 20px;
                border-top: 2px solid {{ colors.text_light }};
                font-size: 11px;
                color: {{ colors.text_light }};
            }
            
            .qr-container {
                text-align: center;
                margin: 20px 0;
            }
            
            .qr-code {
                max-width: 150px;
                height: auto;
            }
            
            .verification-hash {
                font-family: 'Courier New', monospace;
                font-size: 10px;
                background: #F5F5F5;
                padding: 8px;
                border-radius: 4px;
                word-break: break-all;
                margin-top: 10px;
            }
            
            /* Legal disclaimer */
            .disclaimer {
                background: #FFF9E6;
                border-left: 4px solid {{ colors.primary }};
                padding: 15px;
                margin: 20px 0;
                font-size: 11px;
                line-height: 1.5;
            }
            
            .disclaimer-title {
                font-weight: 700;
                color: {{ colors.primary }};
                margin-bottom: 8px;
            }
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="header">
            <div class="logo-container">
                <img src="{{ logo_path }}" alt="Wildfire Recoveries in Argentina" class="logo">
            </div>
            <h1>Certificado de Condición Legal del Terreno</h1>
            <h2>Land Legal Status Certificate</h2>
            <div class="cert-number">{{ certificate_number }}</div>
        </div>
        
        <!-- Status Badge -->
        <div class="status-badge {% if is_prohibited %}status-prohibited{% else %}status-clear{% endif %}">
            {% if is_prohibited %}
                ⛔ TERRENO CON RESTRICCIÓN LEGAL
            {% else %}
                ✅ TERRENO SIN RESTRICCIONES
            {% endif %}
        </div>
        
        <!-- Location Info -->
        <div class="section">
            <div class="section-title">📍 Información del Terreno</div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Coordenadas</div>
                    <div class="info-value">{{ latitude }}°, {{ longitude }}°</div>
                </div>
                <div class="info-item">
                    <div class="info-label">ID Catastral</div>
                    <div class="info-value">{{ cadastral_id or 'No especificado' }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Fecha de Consulta</div>
                    <div class="info-value">{{ query_date }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Estado Legal</div>
                    <div class="info-value">{{ legal_status }}</div>
                </div>
            </div>
        </div>
        
        <!-- Fire Events (if any) -->
        {% if fires|length > 0 %}
        <div class="section">
            <div class="section-title">🔥 Incendios Históricos Detectados</div>
            <table class="fire-table">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Intensidad (FRP)</th>
                        <th>Área Protegida</th>
                        <th>Prohibido Hasta</th>
                    </tr>
                </thead>
                <tbody>
                    {% for fire in fires %}
                    <tr>
                        <td>{{ fire.date }}</td>
                        <td>
                            <span class="fire-intensity {% if fire.frp > 200 %}intensity-high{% elif fire.frp > 100 %}intensity-medium{% else %}intensity-low{% endif %}">
                                {{ fire.frp }} MW
                            </span>
                        </td>
                        <td>{{ fire.protected_area or 'N/A' }}</td>
                        <td><strong>{{ fire.prohibition_until }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}
        
        <!-- Legal Disclaimer -->
        <div class="disclaimer">
            <div class="disclaimer-title">⚖️ Aviso Legal</div>
            <p>
                Este certificado se basa en datos satelitales de NASA FIRMS (VIIRS/MODIS) con resolución de 375-1000m 
                y la legislación vigente (Ley 26.815 Art. 22 bis). Los datos climáticos provienen de ERA5-Land (ECMWF). 
                Este documento es de carácter informativo y no reemplaza consultas legales formales. 
                Para determinaciones oficiales, consulte con las autoridades competentes.
            </p>
        </div>
        
        <!-- Verification Footer -->
        <div class="footer">
            <div class="qr-container">
                <img src="{{ qr_code_url }}" alt="QR Verificación" class="qr-code">
                <p>Escanee para verificar autenticidad en línea</p>
            </div>
            
            <div style="text-align: center; margin-top: 15px;">
                <strong>Hash de Verificación:</strong>
                <div class="verification-hash">{{ verification_hash }}</div>
            </div>
            
            <p style="text-align: center; margin-top: 20px;">
                Emitido: {{ issued_at }} | Válido hasta: {{ valid_until }}<br>
                Wildfire Recoveries in Argentina | https://wildfire-recoveries.ar
            </p>
        </div>
    </body>
    </html>
    """
    
    def generate_certificate_pdf(self, certificate_data: dict, output_path: str):
        """Genera PDF del certificado con branding"""
        
        template = Template(self.CERTIFICATE_TEMPLATE)
        
        html_content = template.render(
            colors=self.COLORS,
            logo_path='file:///path/to/logo-horizontal.svg',  # Ajustar ruta
            **certificate_data
        )
        
        # Generar PDF
        HTML(string=html_content).write_pdf(output_path)
        
        return output_path
```

---

### 2. Frontend (React theme configuration)

```javascript
// frontend/src/theme/colors.js

export const colors = {
  // Colores primarios de la marca
  primary: {
    fireOrange: '#F66A23',
    dangerRed: '#D93725',
    successGreen: '#4F9F4A',
    recoveryGreen: '#A8D875',
  },
  
  // Colores neutros
  neutral: {
    darkGray: '#323232',
    lightGray: '#E0E0E0',
    white: '#FFFFFF',
    black: '#000000',
  },
  
  // Estados de UI (derivados)
  status: {
    success: '#4F9F4A',
    warning: '#F66A23',
    error: '#D93725',
    info: '#3B82F6',
  },
  
  // Variantes para hover/active
  hover: {
    fireOrange: '#E45A13',
    dangerRed: '#C92715',
    successGreen: '#3F8F3A',
    recoveryGreen: '#98C865',
  },
  
  // Mapas (Leaflet)
  map: {
    activeFire: '#F66A23',        // Incendio activo
    highConfidence: '#D93725',    // Alta confianza
    mediumConfidence: '#F66A23',  // Media confianza
    lowConfidence: '#FFA500',     // Baja confianza
    protectedArea: '#4F9F4A',     // Área protegida
    recovery: '#A8D875',          // Recuperación
    noData: '#E0E0E0',            // Sin datos
  },
  
  // Gradientes
  gradients: {
    fireIntensity: 'linear-gradient(135deg, #F66A23 0%, #D93725 100%)',
    recovery: 'linear-gradient(135deg, #4F9F4A 0%, #A8D875 100%)',
    header: 'linear-gradient(90deg, #323232 0%, #4F9F4A 100%)',
  },
}

export default colors
```

```javascript
// frontend/src/theme/index.js

import colors from './colors'

export const theme = {
  colors,
  
  // Tipografía
  fonts: {
    primary: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    monospace: "'Courier New', monospace",
  },
  
  fontSizes: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '24px',
    '2xl': '32px',
    '3xl': '48px',
  },
  
  // Espaciado
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px',
  },
  
  // Border radius
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px',
  },
  
  // Sombras
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  
  // Breakpoints
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
}
```

---

### 3. Componente de Mapa (Leaflet con Colores)

```jsx
// frontend/src/components/FireMap.jsx

import React from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { colors } from '../theme/colors'

const FireMap = ({ fires }) => {
  
  const getFireColor = (fire) => {
    // Color basado en confianza
    if (fire.confidence >= 80) return colors.map.highConfidence
    if (fire.confidence >= 50) return colors.map.mediumConfidence
    return colors.map.lowConfidence
  }
  
  const getFireRadius = (fire) => {
    // Radio basado en FRP (intensidad)
    return Math.min(Math.max(fire.frp / 10, 5), 20)
  }
  
  return (
    <MapContainer
      center={[-34.6037, -58.3816]}
      zoom={6}
      style={{ height: '600px', width: '100%' }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />
      
      {fires.map((fire) => (
        <CircleMarker
          key={fire.id}
          center={[fire.latitude, fire.longitude]}
          radius={getFireRadius(fire)}
          pathOptions={{
            fillColor: getFireColor(fire),
            fillOpacity: 0.7,
            color: colors.neutral.darkGray,
            weight: 1,
          }}
        >
          <Popup>
            <div style={{ fontFamily: theme.fonts.primary }}>
              <h3 style={{ color: colors.primary.fireOrange, marginBottom: '8px' }}>
                🔥 Incendio {fire.date}
              </h3>
              <p><strong>FRP:</strong> {fire.frp} MW</p>
              <p><strong>Confianza:</strong> {fire.confidence}%</p>
              <p><strong>Satélite:</strong> {fire.satellite}</p>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}

export default FireMap
```

---

### 4. Componente de status badge

```jsx
// frontend/src/components/StatusBadge.jsx

import React from 'react'
import styled from 'styled-components'
import { colors } from '../theme/colors'

const Badge = styled.div`
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  
  ${({ variant }) => {
    switch (variant) {
      case 'prohibited':
        return `
          background-color: ${colors.primary.dangerRed};
          color: ${colors.neutral.white};
        `
      case 'clear':
        return `
          background-color: ${colors.primary.successGreen};
          color: ${colors.neutral.white};
        `
      case 'warning':
        return `
          background-color: ${colors.primary.fireOrange};
          color: ${colors.neutral.white};
        `
      case 'recovery':
        return `
          background-color: ${colors.primary.recoveryGreen};
          color: ${colors.neutral.darkGray};
        `
      default:
        return `
          background-color: ${colors.neutral.lightGray};
          color: ${colors.neutral.darkGray};
        `
    }
  }}
`

const StatusBadge = ({ variant, children }) => {
  return <Badge variant={variant}>{children}</Badge>
}

export default StatusBadge

// Uso:
// <StatusBadge variant="prohibited">⛔ PROHIBIDO</StatusBadge>
// <StatusBadge variant="clear">✅ SIN RESTRICCIONES</StatusBadge>
```

---

## 📐 Uso de logo

```jsx
// frontend/src/components/Header.jsx

import React from 'react'
import styled from 'styled-components'

const HeaderContainer = styled.header`
  background: linear-gradient(90deg, #323232 0%, #4F9F4A 100%);
  padding: 20px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
`

const Logo = styled.img`
  height: 50px;
  width: auto;
`

const Header = () => {
  return (
    <HeaderContainer>
      <Logo 
        src="/assets/logos/logo-horizontal-white.svg" 
        alt="Wildfire Recoveries in Argentina"
      />
      <nav>
        {/* Navigation links */}
      </nav>
    </HeaderContainer>
  )
}
```



## Tareas pendientes

- [ ] Guardar logo horizontal en `frontend/public/assets/logos/logo-horizontal.svg`
- [ ] Crear versión blanca del logo para fondos oscuros
- [ ] Generar favicon (16x16, 32x32, 48x48)
- [ ] Configurar `theme.js` con paleta de colores
- [ ] Actualizar template de PDFs con branding
- [ ] Aplicar colores en componentes de mapa
- [ ] Configurar meta tags con logo para redes sociales
