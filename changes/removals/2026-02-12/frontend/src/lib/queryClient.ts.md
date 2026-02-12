# Removal log: frontend/src/lib/queryClient.ts
Date: 2026-02-12

Removed:
```ts
  audit: {
    result: (id: string) => ['audit', id] as const,
  },
  credits: {
    balance: () => ['credits', 'balance'] as const,
    transactions: (page: number) => ['credits', 'transactions', page] as const,
  },
  payments: {
    status: (id: string) => ['payments', id] as const,
  },
```

Reason:
No references to these query keys exist in the repo (search across `frontend/src`), so they were removed to avoid dead code.

Recovery:
Re-add the snippet above inside the `queryKeys` object in `frontend/src/lib/queryClient.ts` if these features are reintroduced.
