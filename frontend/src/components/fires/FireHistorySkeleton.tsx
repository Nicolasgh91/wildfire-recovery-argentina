/**
 * @file FireHistorySkeleton.tsx
 * @description Skeleton loader for FireHistory page.
 */

export function FireHistorySkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between">
        <div className="h-8 w-48 rounded bg-gray-200 animate-pulse" />
        <div className="h-10 w-32 rounded bg-gray-200 animate-pulse" />
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="rounded-lg bg-white p-4">
            <div className="mb-2 h-4 w-24 rounded bg-gray-200 animate-pulse" />
            <div className="h-8 w-16 rounded bg-gray-200 animate-pulse" />
          </div>
        ))}
      </div>
      <div className="rounded-lg bg-white">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="flex gap-4 border-b p-4">
            <div className="h-4 w-24 rounded bg-gray-200 animate-pulse" />
            <div className="h-4 w-32 rounded bg-gray-200 animate-pulse" />
            <div className="h-4 w-20 rounded bg-gray-200 animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}