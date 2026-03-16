type HomeReturnContext = {
    returnTo: 'home'
    home: { scrollY: number }
}

type HistoryReturnContext = {
    returnTo: 'history'
    history: { search?: string; scrollY?: number }
}

type MapReturnContext = {
    returnTo: 'map'
    map: { selectedFireId?: string }
}

export type AuditReturnContext = {
    returnTo: 'audit'
    audit: {
        lat: number
        lon: number
        radius: number
        page: number
    }
}

/** State passed to /fires/:id via location.state when navigating from Home, History, Map or Audit */
export type ReturnContext =
    | HomeReturnContext
    | HistoryReturnContext
    | MapReturnContext
    | AuditReturnContext

/** State passed back to Home or Map via location.state when returning from detail */
export interface RestoreContext {
    restore: { scrollY?: number; selectedFireId?: string }
}

/** sessionStorage key for backup return context */
export const RETURN_CONTEXT_KEY = 'fg:return_context'
