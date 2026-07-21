"use client";

import {
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

interface CandlestickChartProps {
  candles: Candle[];
  overlays: { label: string; color: string; points: IndicatorPoint[] }[];
}

export function CandlestickChart({ candles, overlays }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaySeriesRef = useRef<ISeriesApi<"Line">[]>([]);

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

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      overlaySeriesRef.current = [];
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    if (!chart || !candleSeries) return;

    candleSeries.setData(
      candles.map((c) => ({
        time: (Date.parse(c.open_time) / 1000) as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );

    overlaySeriesRef.current.forEach((series) => chart.removeSeries(series));
    overlaySeriesRef.current = overlays.map((overlay) => {
      const series = chart.addSeries(LineSeries, {
        color: overlay.color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        title: overlay.label,
      });
      series.setData(
        overlay.points.map((p) => ({
          time: p.time as UTCTimestamp,
          value: p.value,
        })),
      );
      return series;
    });

    chart.timeScale().fitContent();
  }, [candles, overlays]);

  return <div ref={containerRef} className="h-[480px] w-full" />;
}
