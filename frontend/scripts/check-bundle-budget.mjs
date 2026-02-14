/**
 * Bundle budget checker (BL-010 / PERF-008).
 *
 * Reads the Vite build output directory and checks each JS chunk
 * against a configurable size budget. Exits with code 1 if any
 * chunk exceeds its budget.
 *
 * Usage:  node scripts/check-bundle-budget.mjs [--budget-kb=600]
 */
import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const DIST_DIR = join(import.meta.dirname, '..', 'dist', 'assets')
const DEFAULT_BUDGET_KB = 600 // per-chunk budget in KB

function parseBudget() {
  const arg = process.argv.find((a) => a.startsWith('--budget-kb='))
  if (arg) return Number(arg.split('=')[1])
  if (process.env.BUDGET_KB) return Number(process.env.BUDGET_KB)
  return DEFAULT_BUDGET_KB
}

const budgetKb = parseBudget()
let failed = false

try {
  const files = readdirSync(DIST_DIR)
  const jsFiles = files.filter((f) => f.endsWith('.js'))

  if (jsFiles.length === 0) {
    console.error('No JS chunks found in', DIST_DIR)
    console.error('Run "npm run build" first.')
    process.exit(1)
  }

  console.log(`\nBundle Budget Check (limit: ${budgetKb} KB per chunk)\n`)
  console.log('%-45s %10s %10s %s', 'Chunk', 'Size (KB)', 'Budget', 'Status')
  console.log('-'.repeat(80))

  for (const file of jsFiles) {
    const filePath = join(DIST_DIR, file)
    const sizeBytes = statSync(filePath).size
    const sizeKb = Math.round(sizeBytes / 1024)
    const ok = sizeKb <= budgetKb
    const status = ok ? '  OK' : '  OVER'

    if (!ok) failed = true

    console.log(
      '%-45s %10d %10d %s',
      file.length > 45 ? file.slice(0, 42) + '...' : file,
      sizeKb,
      budgetKb,
      status,
    )
  }

  console.log('')

  if (failed) {
    console.error('FAIL: One or more chunks exceed the budget.')
    if (process.env.BUDGET_OVERRIDE === 'true') {
      console.warn('BUDGET_OVERRIDE=true — treating as warning only.')
      process.exit(0)
    }
    process.exit(1)
  }

  console.log('PASS: All chunks within budget.')
} catch (err) {
  if (err.code === 'ENOENT') {
    console.error('Build output not found at', DIST_DIR)
    console.error('Run "npm run build" first.')
    process.exit(1)
  }
  throw err
}
