export type UserCredits = {
  balance: number
  last_updated?: string | null
  source?: 'api' | 'fallback'
}
