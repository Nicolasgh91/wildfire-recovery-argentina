# Removal log: frontend/vite.config.ts
Date: 2026-02-12

Removed:
```ts
import { sentryVitePlugin } from "@sentry/vite-plugin";

  const plugins = [
    react(),
    sentryVitePlugin({
      org: "freelnace",
      project: "javascript-react"
    }),
    sentryVitePlugin({
      org: "freelnace",
      project: "javascript-react"
    })
  ]
```

Reason:
The Sentry plugin was registered twice and always enabled. The new config gates uploads on Sentry envs and avoids duplicate plugin registration.

Recovery:
Restore the snippet above in `frontend/vite.config.ts` to re-enable always-on, duplicated Sentry plugin registration.
