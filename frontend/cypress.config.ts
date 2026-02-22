import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:5173',
    supportFile: 'cypress/support/e2e.ts',
    allowCypressEnv: false,
    env: {
      TEST_USER_EMAIL: process.env.CYPRESS_TEST_USER_EMAIL,
      TEST_USER_PASSWORD: process.env.CYPRESS_TEST_USER_PASSWORD,
      API_KEY: process.env.CYPRESS_API_KEY,
      API_BASE_URL: process.env.CYPRESS_API_BASE_URL || 'http://localhost:8000/api/v1',
    },
    defaultCommandTimeout: 15000,
  },
})
