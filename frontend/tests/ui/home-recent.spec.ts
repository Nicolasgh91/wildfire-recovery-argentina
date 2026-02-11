import { test, expect, type Page, type ConsoleMessage } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

const CONSOLE_WHITELIST = [
  /Warning:/,
  /\[vite\]/,
  /chrome-extension/,
  /Leaflet/i,
]

function setupConsoleGuard(page: Page) {
  const errors: string[] = []

  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      const text = msg.text()
      const isWhitelisted = CONSOLE_WHITELIST.some((re) => re.test(text))
      if (!isWhitelisted) errors.push(text)
    }
  })

  page.on('pageerror', (err) => {
    errors.push(`PAGE_ERROR: ${err.message}`)
  })

  return errors
}

test.describe('Home - Activos y recientes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('Toggle recientes si esta disponible', async ({ page }) => {
    const errors = setupConsoleGuard(page)

    await page.goto('/', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('Incendios activos en Argentina')).toBeVisible()

    const toggle = page.getByText('Ver recientes')
    if (await toggle.count()) {
      await toggle.click()
    }

    const emptyState = page.getByText(/No hay incendios activos ni recientes/i)
    const cardTitle = page.getByText(/Incendio en/i)

    if (await cardTitle.count()) {
      await expect(cardTitle.first()).toBeVisible()
    } else {
      await expect(emptyState).toBeVisible()
    }

    expect(errors).toEqual([])
  })
})
