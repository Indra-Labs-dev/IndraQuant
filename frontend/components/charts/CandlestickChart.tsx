"use client";

import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { Candle } from "@/lib/api-client/types";
import type { IndicatorPoint } from "@/lib/indicators";

export type ChartType = "candles" | "area";

interface CandlestickChartProps {
  candles: Candle[];
  overlays: { label: string; color: string; points: IndicatorPoint[] }[];
  /** "candles" (default, detailed) or "area" (simplified mountain chart,
   * easier to read for beginners). */
  chartType?: ChartType;
  /** Identifies the current view (e.g. `${instrumentId}:${timeframe}`).
   * The chart re-fits (zooms to content) only when this changes — not on
   * every periodic/live data refresh, so the user's zoom/pan is preserved. */
  fitKey: string;
}

export function CandlestickChart({
  candles,
  overlays,
  chartType = "candles",
  fitKey,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<"Candlestick"> | ISeriesApi<"Area"> | null>(
    null,
  );
  const mainSeriesTypeRef = useRef<ChartType | null>(null);
  const overlaySeriesRef = useRef<ISeriesApi<"Line">[]>([]);
  const lastFitKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b93a7",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "rgba(139, 147, 167, 0.08)" },
        horzLines: { color: "rgba(139, 147, 167, 0.08)" },
      },
      crosshair: {
        vertLine: { color: "rgba(139, 92, 246, 0.5)", labelBackgroundColor: "#3b82f6" },
        horzLine: { color: "rgba(139, 92, 246, 0.5)", labelBackgroundColor: "#3b82f6" },
      },
      timeScale: { timeVisible: true, borderColor: "rgba(139, 147, 167, 0.2)" },
      rightPriceScale: { borderColor: "rgba(139, 147, 167, 0.2)" },
      autoSize: true,
    });

    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      mainSeriesRef.current = null;
      mainSeriesTypeRef.current = null;
      overlaySeriesRef.current = [];
      lastFitKeyRef.current = null;
    };
  }, []);

  // (Re)create the main series only when the chart type actually changes —
  // switching type deserves a fresh fit, tracked by resetting lastFitKeyRef.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || mainSeriesTypeRef.current === chartType) return;

    if (mainSeriesRef.current) {
      chart.removeSeries(mainSeriesRef.current);
    }

    mainSeriesRef.current =
      chartType === "candles"
        ? chart.addSeries(CandlestickSeries, {
            upColor: "#34d399",
            downColor: "#ef4444",
            borderVisible: false,
            wickUpColor: "#34d399",
            wickDownColor: "#ef4444",
          })
        : chart.addSeries(AreaSeries, {
            lineColor: "#3b82f6",
            topColor: "rgba(59, 130, 246, 0.35)",
            bottomColor: "rgba(139, 92, 246, 0.03)",
            lineWidth: 3,
            priceLineColor: "#8b5cf6",
          });
    mainSeriesTypeRef.current = chartType;
    lastFitKeyRef.current = null;
  }, [chartType]);

  useEffect(() => {
    const chart = chartRef.current;
    const series = mainSeriesRef.current;
    if (!chart || !series) return;

    if (chartType === "candles") {
      (series as ISeriesApi<"Candlestick">).setData(
        candles.map((c) => ({
          time: (Date.parse(c.open_time) / 1000) as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      );
    } else {
      (series as ISeriesApi<"Area">).setData(
        candles.map((c) => ({
          time: (Date.parse(c.open_time) / 1000) as UTCTimestamp,
          value: c.close,
        })),
      );
    }

    overlaySeriesRef.current.forEach((s) => chart.removeSeries(s));
    overlaySeriesRef.current = overlays.map((overlay) => {
      const lineSeries = chart.addSeries(LineSeries, {
        color: overlay.color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        title: overlay.label,
      });
      lineSeries.setData(
        overlay.points.map((p) => ({
          time: p.time as UTCTimestamp,
          value: p.value,
        })),
      );
      return lineSeries;
    });

    if (lastFitKeyRef.current !== fitKey) {
      chart.timeScale().fitContent();
      lastFitKeyRef.current = fitKey;
    }
  }, [candles, overlays, chartType, fitKey]);

  return <div ref={containerRef} className="h-[480px] w-full" />;
}
