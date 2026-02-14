/** State passed to /fires/:id via location.state when navigating from Home or Map */
export interface ReturnContext {
    returnTo: 'home' | 'map'
    home?: { scrollY: number }
    map?: { selectedFireId?: string }
}

/** State passed back to Home or Map via location.state when returning from detail */
export interface RestoreContext {
    restore: { scrollY?: number; selectedFireId?: string }
}

/** sessionStorage key for backup return context */
export const RETURN_CONTEXT_KEY = 'fg:return_context'
