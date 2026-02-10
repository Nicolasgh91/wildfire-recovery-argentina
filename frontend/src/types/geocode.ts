export type GeocodeResult = {
  lat: number
  lon: number
  display_name: string
  boundingbox?: string[] | null
  source?: string
}

export type GeocodeResponse = {
  query: string
  result: GeocodeResult
}
