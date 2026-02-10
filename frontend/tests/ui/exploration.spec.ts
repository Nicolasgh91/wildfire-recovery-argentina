/**
 * @file exploration.spec.ts
 * @description Smoke UI tests for the "Exploración satelital" page (/exploracion).
 *
 * These tests run against the LIVE dataset — no fixtures are inserted.
 * Default language is Spanish (es).
 */

import { test, expect, type Page, type ConsoleMessage } from '@playwright/test'
import { loginAsAdmin } from './helpers/auth'

/* ------------------------------------------------------------------ */
/*  Console-error guard shared across all tests                       */
/* ------------------------------------------------------------------ */

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

/* ================================================================== */
/*  Suite 2: Exploración satelital                                    */
/* ================================================================== */
test.describe('Exploracion satelital - /exploracion', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page)
    })

    test('1 · Carga base', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/exploracion')
        await page.waitForLoadState('networkidle')

        // h1 title
        await expect(
            page.getByRole('heading', { name: /Explorá la evolución del terreno/i }),
        ).toBeVisible()

        // Stepper with 3 steps (numbered circles 1, 2, 3)
        const stepper = page.getByTestId('exploration-stepper')
        await expect(stepper).toBeVisible()
        await expect(stepper.getByText('1')).toBeVisible()
        await expect(stepper.getByText('2')).toBeVisible()
        await expect(stepper.getByText('3')).toBeVisible()

        // "Elegí un incendio" card
        await expect(page.getByText('Provincia').first()).toBeVisible()

        // "Buscar" and "Elegir en el mapa" buttons
        await expect(page.getByTestId('exploration-btn-search')).toBeVisible()
        await expect(page.getByTestId('exploration-btn-map')).toBeVisible()

        // Results panel
        await expect(page.getByTestId('exploration-results')).toBeVisible()

        expect(errors).toEqual([])
    })

    test('2 · Búsqueda vacía controlada', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/exploracion')
        await page.waitForLoadState('networkidle')

        // Click "Buscar" without any filters
        await page.getByTestId('exploration-btn-search').click()

        // Should either show "No encontramos incendios" or display results
        // (depends on the dataset — both are valid states)
        const resultArea = page.getByTestId('exploration-results')
        await expect(resultArea).toBeVisible()

        // Wait for search to complete
        await page.waitForTimeout(3000)

        // Verify no crashes — the page should still be interactive
        await expect(page.getByTestId('exploration-btn-search')).toBeEnabled()

        const unexpectedErrors = errors.filter((msg) => !/status of 422/i.test(msg))
        expect(unexpectedErrors).toEqual([])
    })

    test('3 · Abrir sección "Tengo el ID del evento"', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/exploracion')
        await page.waitForLoadState('networkidle')

        // Expand the accordion
        const accordionTrigger = page.getByRole('button', { name: /Tengo el ID del evento/i })
        await accordionTrigger.click()

        // ID input should now be visible
        const idInput = page.getByPlaceholder('UUID del incendio')
        await expect(idInput).toBeVisible()

        // Type an invalid UUID
        await idInput.fill('invalid-uuid-12345')

        // Click "Cargar evento"
        await page.getByRole('button', { name: /Cargar evento/i }).click()

        // Should show an error toast or controlled failure — wait for it
        await page.waitForTimeout(3000)

        // The page should still be functional (no crash)
        await expect(accordionTrigger).toBeVisible()
        await expect(page.getByTestId('exploration-btn-search')).toBeEnabled()

        const unexpectedErrors = errors.filter((msg) => !/status of 422/i.test(msg))
        expect(unexpectedErrors).toEqual([])
    })
})
