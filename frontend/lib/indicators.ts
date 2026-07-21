import type { Candle } from "@/lib/api-client/types";

export interface IndicatorPoint {
  time: number;
  value: number;
}

export function simpleMovingAverage(
  candles: Candle[],
  period: number,
): IndicatorPoint[] {
  const points: IndicatorPoint[] = [];
  let windowSum = 0;
  for (let i = 0; i < candles.length; i++) {
    windowSum += candles[i].close;
    if (i >= period) {
      windowSum -= candles[i - period].close;
    }
    if (i >= period - 1) {
      points.push({
        time: Date.parse(candles[i].open_time) / 1000,
        value: windowSum / period,
      });
    }
  }
  return points;
}
