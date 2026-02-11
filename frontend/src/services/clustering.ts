import type { FireSearchItem } from '@/types/fire'

export type EpisodeGroup = {
  id: string
  representative: FireSearchItem
  events: FireSearchItem[]
  start_date: string
  end_date: string
  centroid: { latitude: number; longitude: number } | null
}

const DISTANCE_THRESHOLD_KM = 2.5
const WINDOW_HOURS = 48
const WINDOW_MS = WINDOW_HOURS * 60 * 60 * 1000

type InternalGroup = {
  id: string
  representative: FireSearchItem
  events: FireSearchItem[]
  startMs: number
  endMs: number
  centroidLatSum: number
  centroidLonSum: number
  centroidCount: number
}

function toTime(value?: string | null): number | null {
  if (!value) return null
  const time = Date.parse(value)
  if (Number.isNaN(time)) return null
  return time
}

function formatDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRad = (value: number) => (value * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  return 2 * 6371 * Math.asin(Math.sqrt(a))
}

function getEventRange(event: FireSearchItem): { startMs: number; endMs: number } {
  const startMs = toTime(event.start_date) ?? 0
  const endMs = toTime(event.end_date) ?? startMs
  return { startMs, endMs }
}

function getEventRecency(event: FireSearchItem): number {
  const { endMs, startMs } = getEventRange(event)
  return endMs || startMs
}

function getEventCentroid(event: FireSearchItem) {
  if (!event.centroid) return null
  const { latitude, longitude } = event.centroid
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return { latitude, longitude }
}

function canJoinGroup(group: InternalGroup, event: FireSearchItem): number | null {
  const centroid = getEventCentroid(event)
  if (!centroid || group.centroidCount === 0) return null

  const groupLat = group.centroidLatSum / group.centroidCount
  const groupLon = group.centroidLonSum / group.centroidCount
  const distance = haversineKm(groupLat, groupLon, centroid.latitude, centroid.longitude)
  if (distance > DISTANCE_THRESHOLD_KM) return null

  const { startMs, endMs } = getEventRange(event)
  const withinWindow = startMs <= group.endMs + WINDOW_MS && endMs >= group.startMs - WINDOW_MS
  if (!withinWindow) return null

  return distance
}

function addEventToGroup(group: InternalGroup, event: FireSearchItem) {
  group.events.push(event)

  const { startMs, endMs } = getEventRange(event)
  group.startMs = Math.min(group.startMs, startMs)
  group.endMs = Math.max(group.endMs, endMs)

  const centroid = getEventCentroid(event)
  if (centroid) {
    group.centroidLatSum += centroid.latitude
    group.centroidLonSum += centroid.longitude
    group.centroidCount += 1
  }

  if (getEventRecency(event) > getEventRecency(group.representative)) {
    group.representative = event
  }
}

function createGroup(event: FireSearchItem, index: number): InternalGroup {
  const { startMs, endMs } = getEventRange(event)
  const centroid = getEventCentroid(event)
  return {
    id: `episode-group-${index}`,
    representative: event,
    events: [event],
    startMs,
    endMs,
    centroidLatSum: centroid ? centroid.latitude : 0,
    centroidLonSum: centroid ? centroid.longitude : 0,
    centroidCount: centroid ? 1 : 0,
  }
}

export function groupEventsByEpisode(events: FireSearchItem[]): EpisodeGroup[] {
  if (!events.length) return []

  const sorted = [...events].sort((a, b) => {
    const aTime = getEventRecency(a)
    const bTime = getEventRecency(b)
    return aTime - bTime
  })

  const groups: InternalGroup[] = []

  sorted.forEach((event, index) => {
    const centroid = getEventCentroid(event)
    if (!centroid) {
      groups.push(createGroup(event, index))
      return
    }

    let bestGroup: InternalGroup | null = null
    let bestDistance = Number.POSITIVE_INFINITY

    for (const group of groups) {
      const distance = canJoinGroup(group, event)
      if (distance === null) continue
      if (distance < bestDistance) {
        bestDistance = distance
        bestGroup = group
      }
    }

    if (!bestGroup) {
      groups.push(createGroup(event, index))
      return
    }

    addEventToGroup(bestGroup, event)
  })

  return groups.map((group) => {
    const centroid =
      group.centroidCount > 0
        ? {
            latitude: group.centroidLatSum / group.centroidCount,
            longitude: group.centroidLonSum / group.centroidCount,
          }
        : null

    return {
      id: group.id,
      representative: group.representative,
      events: group.events,
      start_date: formatDate(group.startMs),
      end_date: formatDate(group.endMs),
      centroid,
    }
  })
}
