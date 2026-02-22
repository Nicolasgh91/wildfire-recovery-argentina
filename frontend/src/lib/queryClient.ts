/**
 * @file queryClient.ts
 * @description TanStack Query configuration.
 */

import { QueryClient } from '@tanstack/react-query'

export const QUERY_CONFIG = {
  STALE_TIME: 5 * 60 * 1000,
  GC_TIME: 30 * 60 * 1000,
}

export const queryKeys = {
  fires: {
    all: ['fires'] as const,
    list: (filters: object) => ['fires', 'list', filters] as const,
    active: (limit: number) => ['fires', 'active', limit] as const,
    detail: (id: string) => ['fires', 'detail', id] as const,
    stats: (filters: object) => ['fires', 'stats', filters] as const,
  },
  episodes: {
    active: (limit: number) => ['episodes', 'active', limit] as const,
    mode: (mode: string, limit: number) => ['episodes', mode, limit] as const,
  },
  quality: {
    fire: (id: string) => ['quality', 'fire', id] as const,
  },
  explorations: {
    all: ['explorations'] as const,
    detail: (id: string) => ['explorations', 'detail', id] as const,
    items: (id: string) => ['explorations', 'items', id] as const,
    quote: (id: string) => ['explorations', 'quote', id] as const,
    assets: (id: string) => ['explorations', 'assets', id] as const,
  },
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: QUERY_CONFIG.STALE_TIME,
      gcTime: QUERY_CONFIG.GC_TIME,
      retry: 3,
      refetchOnWindowFocus: true,
    },
  },
})
