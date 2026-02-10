/**
 * @file verify-land.spec.ts
 * @description Smoke UI tests for the "Verificar terreno" page (/audit).
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
    // React dev-mode warnings
    /Warning:/,
    // Vite HMR noise
    /\[vite\]/,
    // Browser extension noise
    /chrome-extension/,
    // Known Leaflet warning
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
/*  Suite 1: Verificar terreno                                        */
/* ================================================================== */

test.describe('Verificar terreno - /audit', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page)
    })

    test('1 · Carga base', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/audit')
        await page.waitForLoadState('networkidle')

        // h1 title
        await expect(
            page.getByRole('heading', { name: 'Verificar terreno', level: 1 }),
        ).toBeVisible()

        // Search input placeholder
        await expect(
            page.getByPlaceholder(/Dirección, localidad/),
        ).toBeVisible()

        // Area preset buttons
        await expect(page.getByRole('button', { name: 'Alrededores (500 m)' })).toBeVisible()
        await expect(page.getByRole('button', { name: 'Zona (1 km)' })).toBeVisible()
        await expect(page.getByRole('button', { name: 'Amplio (3 km)' })).toBeVisible()

        // Submit button "Verificá"
        await expect(page.getByTestId('audit-submit')).toBeVisible()

        // Checklist card
        await expect(page.getByText('Checklist de verificación')).toBeVisible()

        // Results card
        const resultsHeadings = page.getByText('Resultados')
        await expect(resultsHeadings.first()).toBeVisible()

        expect(errors).toEqual([])
    })

    test('2 · Interacción mínima sin romper', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/audit')
        await page.waitForLoadState('networkidle')

        // -- Click "Zona (1 km)" and verify it becomes selected (variant=default)
        const zonaBtn = page.getByRole('button', { name: 'Zona (1 km)' })
        await zonaBtn.click()
        // When selected the button doesn't have variant="outline" → it gets the
        // primary bg. We just verify it's still visible (no crash).
        await expect(zonaBtn).toBeVisible()

        // -- Expand "Opciones avanzadas"
        const advancedTrigger = page.getByRole('button', { name: /Opciones avanzadas/i })
        await advancedTrigger.click()

        // Latitude and Longitude inputs should now be visible
        await expect(page.getByPlaceholder('-38.4161')).toBeVisible()
        await expect(page.getByPlaceholder('-63.6167')).toBeVisible()

        // -- Submit availability depends on whether the page already has a map point
        const submitBtn = page.getByTestId('audit-submit')

        if (await submitBtn.isDisabled()) {
            await page.getByPlaceholder('-38.4161').fill('-38.4161')
            await page.getByPlaceholder('-63.6167').fill('-63.6167')
            await page.waitForTimeout(300)
            await expect(submitBtn).toBeEnabled()
        } else {
            await expect(submitBtn).toBeEnabled()
        }

        // -- Click "Verificá" and verify loading state appears
        await submitBtn.click()

        // Either the loading spinner shows up or we get results quickly
        const loadingOrResult = page.getByText(/Buscando incendios|Resultados|No se encontraron|Incendios encontrados|No se pudo verificar/)
        await expect(loadingOrResult.first()).toBeVisible({ timeout: 10000 })

        // -- Collapse "Opciones avanzadas" (toggle back)
        await advancedTrigger.click()
        await expect(page.getByPlaceholder('-38.4161')).toBeHidden()

        expect(errors).toEqual([])
    })

    test('3 · No duplicar requests', async ({ page }) => {
        const errors = setupConsoleGuard(page)

        await page.goto('/audit')
        await page.waitForLoadState('networkidle')

        // Track requests to the audit endpoint
        const auditRequests: string[] = []
        page.on('request', (req) => {
            if (req.url().includes('/audit/land-use') && req.method() === 'POST') {
                auditRequests.push(req.url())
            }
        })

        // Expand advanced options and fill coordinates
        await page.getByRole('button', { name: /Opciones avanzadas/i }).click()
        await page.getByPlaceholder('-38.4161').fill('-38.4161')
        await page.getByPlaceholder('-63.6167').fill('-63.6167')
        await page.waitForTimeout(300)

        // Click "Verificá" once
        await page.getByTestId('audit-submit').click()

        // Wait for request to complete
        await page.waitForTimeout(3000)

        // Assert exactly 1 request
        expect(auditRequests).toHaveLength(1)

        expect(errors).toEqual([])
    })
})
