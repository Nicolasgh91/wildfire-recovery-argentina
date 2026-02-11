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

test.describe('Audit - busqueda historica', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page)
  })

  test('Busca por provincia y muestra resultados o error controlado', async ({ page }) => {
    const errors = setupConsoleGuard(page)

    await page.goto('/audit', { waitUntil: 'domcontentloaded' })

    await page.getByTestId('search-place').fill('Chubut')
    await page.getByTestId('audit-submit').click()

    const resolved = page.getByText(/Lugar resuelto/i)
    const error = page.getByText(/No pudimos ubicar ese lugar/i)
    const empty = page.getByText(/No se encontraron episodios/i)

    await Promise.race([
      resolved.waitFor({ state: 'visible' }),
      error.waitFor({ state: 'visible' }),
      empty.waitFor({ state: 'visible' }),
    ])

    if (await resolved.isVisible()) {
      await expect(resolved).toBeVisible()
    } else if (await empty.isVisible()) {
      await expect(empty).toBeVisible()
    } else {
      await expect(error).toBeVisible()
    }

    expect(errors).toEqual([])
  })
})
