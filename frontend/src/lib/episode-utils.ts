import type { EpisodeListItem, EpisodeStatus } from '@/types/episode'

const VALID_STATUSES: EpisodeStatus[] = ['active', 'monitoring', 'extinct', 'closed']

/**
 * Resolves the display status of an episode. If status is missing or invalid, returns 'extinct'.
 */
export function resolveStatus(episode: EpisodeListItem): EpisodeStatus {
  const status = episode.status
  if (status && VALID_STATUSES.includes(status)) {
    return status
  }
  return 'extinct'
}

/** Minimum estimated area (ha) to consider an episode a "large focus" for quick filter. */
export const GRANDES_FOCOS_HA = 500
