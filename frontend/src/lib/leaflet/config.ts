export const MAP_CONFIG = {
  center: [-38.4161, -63.6167] as [number, number], // Argentina center
  zoom: 5,
  minZoom: 4,
  maxZoom: 18,
  maxBounds: [
    [-56, -76], // SW Argentina
    [-21, -53], // NE Argentina
  ] as [[number, number], [number, number]],
}

export const TILE_LAYERS = {
  light: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
  terrain: {
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://opentopomap.org/">OpenTopoMap</a>',
  },
}
