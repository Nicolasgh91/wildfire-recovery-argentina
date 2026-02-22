export interface Fire {
  id: string
  title: string
  lat: number
  lon: number
  severity: 'high' | 'medium' | 'low'
  province: string
  status: 'active' | 'extinguished'
  date: string
  hectares: number
  reliabilityScore: number
  landUseStatus: string
  ndviHistory: { month: string; value: number }[]
  thumbnailUrl: string
}

export interface Certificate {
  id: string
  cadastralId: string
  ownerName: string
  issueDate: string
  status: 'valid' | 'invalid'
}

export interface Shelter {
  id: string
  name: string
  lat: number
  lon: number
}

export const fires: Fire[] = [
  {
    id: 'fire-001',
    title: 'Incendio Sierra de Córdoba',
    lat: -31.4201,
    lon: -64.1888,
    severity: 'high',
    province: 'Córdoba',
    status: 'active',
    date: '2026-01-15',
    hectares: 2500,
    reliabilityScore: 87,
    landUseStatus: 'Prohibited Land Use',
    ndviHistory: [
      { month: 'Aug', value: 0.72 },
      { month: 'Sep', value: 0.45 },
      { month: 'Oct', value: 0.22 },
      { month: 'Nov', value: 0.18 },
      { month: 'Dec', value: 0.25 },
      { month: 'Jan', value: 0.38 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-002',
    title: 'Incendio Bosque Patagónico',
    lat: -42.7692,
    lon: -65.0385,
    severity: 'high',
    province: 'Chubut',
    status: 'active',
    date: '2026-01-20',
    hectares: 5200,
    reliabilityScore: 92,
    landUseStatus: 'Protected Area',
    ndviHistory: [
      { month: 'Aug', value: 0.68 },
      { month: 'Sep', value: 0.65 },
      { month: 'Oct', value: 0.31 },
      { month: 'Nov', value: 0.12 },
      { month: 'Dec', value: 0.19 },
      { month: 'Jan', value: 0.28 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-003',
    title: 'Incendio Delta del Paraná',
    lat: -33.7167,
    lon: -59.2500,
    severity: 'medium',
    province: 'Entre Ríos',
    status: 'extinguished',
    date: '2025-12-10',
    hectares: 1200,
    reliabilityScore: 78,
    landUseStatus: 'Under Review',
    ndviHistory: [
      { month: 'Aug', value: 0.55 },
      { month: 'Sep', value: 0.52 },
      { month: 'Oct', value: 0.38 },
      { month: 'Nov', value: 0.42 },
      { month: 'Dec', value: 0.51 },
      { month: 'Jan', value: 0.58 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-004',
    title: 'Incendio Quebrada de Humahuaca',
    lat: -23.1992,
    lon: -65.3503,
    severity: 'low',
    province: 'Jujuy',
    status: 'extinguished',
    date: '2025-11-28',
    hectares: 340,
    reliabilityScore: 95,
    landUseStatus: 'No Restrictions',
    ndviHistory: [
      { month: 'Aug', value: 0.41 },
      { month: 'Sep', value: 0.38 },
      { month: 'Oct', value: 0.29 },
      { month: 'Nov', value: 0.35 },
      { month: 'Dec', value: 0.42 },
      { month: 'Jan', value: 0.48 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-005',
    title: 'Incendio Sierras de San Luis',
    lat: -33.2950,
    lon: -66.3356,
    severity: 'medium',
    province: 'San Luis',
    status: 'active',
    date: '2026-01-22',
    hectares: 890,
    reliabilityScore: 81,
    landUseStatus: 'Prohibited Land Use',
    ndviHistory: [
      { month: 'Aug', value: 0.62 },
      { month: 'Sep', value: 0.58 },
      { month: 'Oct', value: 0.35 },
      { month: 'Nov', value: 0.21 },
      { month: 'Dec', value: 0.29 },
      { month: 'Jan', value: 0.36 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-006',
    title: 'Incendio Yungas Tucumanas',
    lat: -26.8241,
    lon: -65.2226,
    severity: 'high',
    province: 'Tucumán',
    status: 'active',
    date: '2026-01-25',
    hectares: 1850,
    reliabilityScore: 89,
    landUseStatus: 'Protected Area',
    ndviHistory: [
      { month: 'Aug', value: 0.78 },
      { month: 'Sep', value: 0.71 },
      { month: 'Oct', value: 0.42 },
      { month: 'Nov', value: 0.25 },
      { month: 'Dec', value: 0.31 },
      { month: 'Jan', value: 0.39 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-007',
    title: 'Incendio Meseta Neuquina',
    lat: -38.9516,
    lon: -68.0591,
    severity: 'low',
    province: 'Neuquén',
    status: 'extinguished',
    date: '2025-12-05',
    hectares: 520,
    reliabilityScore: 74,
    landUseStatus: 'No Restrictions',
    ndviHistory: [
      { month: 'Aug', value: 0.45 },
      { month: 'Sep', value: 0.42 },
      { month: 'Oct', value: 0.38 },
      { month: 'Nov', value: 0.45 },
      { month: 'Dec', value: 0.52 },
      { month: 'Jan', value: 0.58 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-008',
    title: 'Incendio Chaco Seco',
    lat: -26.4000,
    lon: -60.7500,
    severity: 'medium',
    province: 'Chaco',
    status: 'active',
    date: '2026-01-18',
    hectares: 3100,
    reliabilityScore: 83,
    landUseStatus: 'Under Review',
    ndviHistory: [
      { month: 'Aug', value: 0.52 },
      { month: 'Sep', value: 0.48 },
      { month: 'Oct', value: 0.32 },
      { month: 'Nov', value: 0.22 },
      { month: 'Dec', value: 0.28 },
      { month: 'Jan', value: 0.35 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-009',
    title: 'Incendio Precordillera Mendocina',
    lat: -32.8908,
    lon: -68.8272,
    severity: 'low',
    province: 'Mendoza',
    status: 'extinguished',
    date: '2025-11-15',
    hectares: 280,
    reliabilityScore: 91,
    landUseStatus: 'No Restrictions',
    ndviHistory: [
      { month: 'Aug', value: 0.38 },
      { month: 'Sep', value: 0.35 },
      { month: 'Oct', value: 0.31 },
      { month: 'Nov', value: 0.38 },
      { month: 'Dec', value: 0.45 },
      { month: 'Jan', value: 0.52 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
  {
    id: 'fire-010',
    title: 'Incendio Selva Misionera',
    lat: -26.9211,
    lon: -54.6167,
    severity: 'high',
    province: 'Misiones',
    status: 'active',
    date: '2026-01-28',
    hectares: 1650,
    reliabilityScore: 86,
    landUseStatus: 'Protected Area',
    ndviHistory: [
      { month: 'Aug', value: 0.82 },
      { month: 'Sep', value: 0.78 },
      { month: 'Oct', value: 0.55 },
      { month: 'Nov', value: 0.32 },
      { month: 'Dec', value: 0.38 },
      { month: 'Jan', value: 0.45 },
    ],
    thumbnailUrl: '/fire-placeholder.jpg',
  },
]

export const shelters: Shelter[] = [
  { id: 'shelter-001', name: 'Refugio Frey', lat: -41.1500, lon: -71.4500 },
  { id: 'shelter-002', name: 'Refugio Italia', lat: -41.1667, lon: -71.4667 },
  { id: 'shelter-003', name: 'Refugio López', lat: -41.0833, lon: -71.5333 },
  { id: 'shelter-004', name: 'Refugio Laguna Negra', lat: -41.1333, lon: -71.5000 },
  { id: 'shelter-005', name: 'Refugio San Martín', lat: -41.1000, lon: -71.4833 },
]

export const provinces = [
  'Córdoba',
  'Chubut',
  'Entre Ríos',
  'Jujuy',
  'San Luis',
  'Tucumán',
  'Neuquén',
  'Chaco',
  'Mendoza',
  'Misiones',
]

export function runAudit(lat: number, lon: number): { restricted: boolean; message: string; expiry?: string } {
  // Mock logic: randomly determine if location is in protected area
  void lat
  void lon
  const isProtected = Math.random() > 0.5
  
  if (isProtected) {
    return {
      restricted: true,
      message: 'This location intersects with a Protected Area zone affected by recent wildfires.',
      expiry: '2075-12-31',
    }
  }
  
  return {
    restricted: false,
    message: 'No land use restrictions found for this location.',
  }
}

export function verifyCertificate(certificateId: string): Certificate | null {
  // Mock verification
  if (certificateId.startsWith('CERT-')) {
    return {
      id: certificateId,
      cadastralId: 'CAD-' + Math.random().toString(36).substring(7).toUpperCase(),
      ownerName: 'Juan Pérez',
      issueDate: '2026-01-15',
      status: 'valid',
    }
  }
  return null
}
