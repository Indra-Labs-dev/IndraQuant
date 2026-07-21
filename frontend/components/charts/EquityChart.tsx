"use client";

import {
  AreaSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { EquityPoint } from "@/lib/api-client/types";

export function EquityChart({ points }: { points: EquityPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b93a7",
      },
      grid: {
        vertLines: { color: "rgba(139, 147, 167, 0.08)" },
        horzLines: { color: "rgba(139, 147, 167, 0.08)" },
      },
      timeScale: { timeVisible: true, borderColor: "rgba(139, 147, 167, 0.2)" },
      rightPriceScale: { borderColor: "rgba(139, 147, 167, 0.2)" },
      autoSize: true,
    });
    seriesRef.current = chart.addSeries(AreaSeries, {
      lineColor: "#3b82f6",
      topColor: "rgba(59, 130, 246, 0.25)",
      bottomColor: "rgba(139, 92, 246, 0.02)",
      lineWidth: 2,
    });
    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    seriesRef.current.setData(
      points.map((p) => ({
        time: (Date.parse(p.time) / 1000) as UTCTimestamp,
        value: p.equity,
      })),
    );
    chartRef.current.timeScale().fitContent();
  }, [points]);

  return <div ref={containerRef} className="h-[320px] w-full" />;
}
