"use client";

import type { CalibrationBucket } from "@/lib/api-client/types";

/** One bar per confidence bucket: the violet fill is the *observed* accuracy,
 * the vertical marker is the bucket's own nominal confidence (perfect
 * calibration = fill reaches exactly the marker). */
export function CalibrationChart({ buckets }: { buckets: CalibrationBucket[] }) {
  return (
    <div className="space-y-2">
      {buckets.map((bucket) => {
        const midpoint = (bucket.low + bucket.high) / 2;
        return (
          <div key={bucket.low} className="flex items-center gap-3 text-xs">
            <span className="w-16 shrink-0 text-[var(--muted)]">
              {Math.round(bucket.low * 100)}-{Math.round(bucket.high * 100)} %
            </span>
            <div className="relative h-4 flex-1 overflow-hidden rounded bg-white/5">
              <div
                className="absolute inset-y-0 w-px bg-[var(--muted)]"
                style={{ left: `${midpoint * 100}%` }}
              />
              {bucket.accuracy !== null && (
                <div
                  className="absolute inset-y-0 rounded bg-[var(--accent-violet)]"
                  style={{ width: `${bucket.accuracy * 100}%` }}
                />
              )}
            </div>
            <span className="w-28 shrink-0 text-right text-[var(--muted)]">
              {bucket.accuracy !== null
                ? `${(bucket.accuracy * 100).toFixed(0)} % (n=${bucket.n})`
                : `n=${bucket.n}`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
