export const MAX_REPORT_IMAGES = 12
export const DEFAULT_REPORT_IMAGES = 12

export function calculateReportCost(imageCount: number) {
  if (!Number.isFinite(imageCount)) return 0
  const normalized = Math.round(imageCount)
  return Math.max(0, Math.min(MAX_REPORT_IMAGES, normalized))
}
