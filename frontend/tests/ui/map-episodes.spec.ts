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

test.describe('Mapa - episodios activos y recientes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('Carga mapa y leyenda', async ({ page }) => {
    const errors = setupConsoleGuard(page)

    await page.goto('/map', { waitUntil: 'domcontentloaded' })

    await expect(page.getByText('Mapa Interactivo')).toBeVisible()
    await expect(page.getByText('Activos')).toBeVisible()
    await expect(page.getByText(/Recientes/i)).toBeVisible()

    const emptyState = page.getByText(/No hay incendios activos ni recientes/i)
    const listItem = page.getByText(/Incendio en/i)

    if (await listItem.count()) {
      await expect(listItem.first()).toBeVisible()
    } else {
      await expect(emptyState).toBeVisible()
    }

    expect(errors).toEqual([])
  })
})
