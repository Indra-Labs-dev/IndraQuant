"use client";

import type { AccuracyTrendPoint } from "@/lib/api-client/types";

/** Sequential index (not calendar time) on the x-axis, so this is a small
 * dependency-free SVG line rather than a financial time-series chart. */
export function RollingAccuracyChart({ points }: { points: AccuracyTrendPoint[] }) {
  if (points.length === 0) return null;

  const width = 100;
  const height = 100;
  const maxIndex = points[points.length - 1].index;
  const toX = (index: number) =>
    maxIndex <= 1 ? 0 : ((index - 1) / (maxIndex - 1)) * width;
  const toY = (accuracy: number) => height - accuracy * height;

  const path = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${toX(p.index).toFixed(2)} ${toY(p.rolling_accuracy).toFixed(2)}`,
    )
    .join(" ");

  return (
    <div className="h-[240px] w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="h-full w-full"
      >
        <line
          x1="0"
          y1={toY(0.5)}
          x2={width}
          y2={toY(0.5)}
          stroke="rgba(139, 147, 167, 0.3)"
          strokeWidth="0.4"
          strokeDasharray="2,2"
          vectorEffect="non-scaling-stroke"
        />
        <path
          d={path}
          fill="none"
          stroke="#8b5cf6"
          strokeWidth="1.4"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}
