export const Z_INDEX = {
  MAP_TILES: 0,
  MAP_CONTROLS: 100,
  MAP_OVERLAYS: 200,
  NAVBAR: 300,
  DRAWER_BACKDROP: 400,
  DRAWER_CONTENT: 500,
  MODAL_CRITICAL: 600,
  TOAST: 700,
} as const

export type ZIndexToken = keyof typeof Z_INDEX

