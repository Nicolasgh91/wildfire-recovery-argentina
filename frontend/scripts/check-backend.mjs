const baseUrl = (process.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const healthUrl = `${baseUrl}/health`

try {
  const response = await fetch(healthUrl)
  if (!response.ok) {
    console.error(`Backend health check failed (${response.status}) at ${healthUrl}`)
    process.exit(1)
  }
  console.log(`Backend health check OK at ${healthUrl}`)
} catch (error) {
  console.error(`Backend health check error at ${healthUrl}`)
  console.error(error instanceof Error ? error.message : error)
  process.exit(1)
}
