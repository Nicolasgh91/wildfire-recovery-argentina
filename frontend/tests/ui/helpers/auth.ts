import { type Page } from '@playwright/test'

const DEFAULT_ADMIN_EMAIL = 'test.admin@forestguard.ar'
const DEFAULT_ADMIN_PASSWORD = 'ForestGuard_Admin_2026!'

function getAdminCredentials() {
  const email =
    process.env.PLAYWRIGHT_ADMIN_EMAIL ??
    process.env.TEST_ADMIN_EMAIL ??
    process.env.CYPRESS_TEST_ADMIN_EMAIL ??
    DEFAULT_ADMIN_EMAIL

  const password =
    process.env.PLAYWRIGHT_ADMIN_PASSWORD ??
    process.env.TEST_ADMIN_PASSWORD ??
    process.env.CYPRESS_TEST_ADMIN_PASSWORD ??
    DEFAULT_ADMIN_PASSWORD

  return { email, password }
}

export async function loginAsAdmin(page: Page) {
  const { email, password } = getAdminCredentials()

  await page.goto('/login')
  await page.getByTestId('login-email').fill(email)
  await page.getByTestId('login-password').fill(password)
  await page.getByTestId('login-submit').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20_000 })
}
