import { defineConfig } from '@playwright/test'

export default defineConfig({
    testDir: './tests/ui',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',

    use: {
        baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },

    projects: [
        {
            name: 'chromium',
            use: { browserName: 'chromium' },
        },
    ],
})
