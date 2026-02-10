type FireCardSkeletonProps = {
  count?: number
}

export function FireCardSkeleton({ count = 1 }: FireCardSkeletonProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={`fire-skeleton-${idx}`}
          className="animate-pulse rounded-lg border border-border bg-background p-4"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="h-3 w-20 rounded bg-slate-200" />
              <div className="h-4 w-32 rounded bg-slate-200" />
              <div className="h-3 w-24 rounded bg-slate-200" />
            </div>
            <div className="h-6 w-20 rounded-full bg-slate-200" />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {Array.from({ length: 8 }).map((__, cellIdx) => (
              <div key={`fire-skeleton-cell-${idx}-${cellIdx}`} className="space-y-1">
                <div className="h-3 w-16 rounded bg-slate-200" />
                <div className="h-3 w-20 rounded bg-slate-200" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
