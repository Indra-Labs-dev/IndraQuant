"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { CandlestickChart, type ChartType } from "@/components/charts/CandlestickChart";
import { AppNav } from "@/components/layout/AppNav";
import {
  getIndicators,
  getInstruments,
  getOhlcv,
  getPatterns,
  getPrediction,
  getSmc,
  marketDataWsUrl,
} from "@/lib/api-client/client";
import type {
  Candle,
  DirectionPrediction,
  Instrument,
  PatternDetection,
  SmcDetection,
} from "@/lib/api-client/types";
import { simpleMovingAverage } from "@/lib/indicators";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1s", "5s", "30s", "1m", "5m", "15m", "1h", "4h", "1d"] as const;
const TIMEFRAME_SECONDS: Record<string, number> = {
  "1s": 1,
  "5s": 5,
  "30s": 30,
  "1m": 60,
  "5m": 300,
  "15m": 900,
  "1h": 3600,
  "4h": 14400,
  "1d": 86400,
};
const VISIBLE_CANDLES = 300;
const REFRESH_INTERVAL_MS = 60_000;

function fetchCandles(instrumentId: number, timeframe: string) {
  const to = new Date();
  const from = new Date(
    to.getTime() - VISIBLE_CANDLES * TIMEFRAME_SECONDS[timeframe] * 1000,
  );
  return getOhlcv(instrumentId, timeframe, from, to, 500);
}

function fetchPatterns(instrumentId: number, timeframe: string) {
  const to = new Date();
  const from = new Date(
    to.getTime() - VISIBLE_CANDLES * TIMEFRAME_SECONDS[timeframe] * 1000,
  );
  return getPatterns(instrumentId, timeframe, from, to, 500);
}

function mergeCandles(existing: Candle[], incoming: Candle[]): Candle[] {
  if (incoming.length === 0) return existing;
  const byTime = new Map(existing.map((c) => [c.open_time, c]));
  for (const candle of incoming) {
    byTime.set(candle.open_time, candle);
  }
  return [...byTime.values()].sort((a, b) =>
    a.open_time.localeCompare(b.open_time),
  );
}

function fetchRsi(instrumentId: number, timeframe: string) {
  const to = new Date();
  const from = new Date(
    to.getTime() - VISIBLE_CANDLES * TIMEFRAME_SECONDS[timeframe] * 1000,
  );
  return getIndicators(instrumentId, timeframe, from, to, "rsi:14", 500);
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | null>(null);
  const [timeframe, setTimeframe] = useState<string>("1h");
  const [chartType, setChartType] = useState<ChartType>("candles");
  const [data, setData] = useState<{ key: string; candles: Candle[] } | null>(
    null,
  );
  const [patterns, setPatterns] = useState<PatternDetection[]>([]);
  const [smc, setSmc] = useState<SmcDetection[]>([]);
  const [prediction, setPrediction] = useState<DirectionPrediction | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState(false);
  const [rsi, setRsi] = useState<number | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dataKey = `${instrumentId}:${timeframe}`;
  const candles = useMemo(
    () => (data?.key === dataKey ? data.candles : []),
    [data, dataKey],
  );
  const loading = !error && data?.key !== dataKey;

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    getInstruments()
      .then((response) => {
        setInstruments(response.instruments);
        setInstrumentId((current) => current ?? response.instruments[0]?.id ?? null);
      })
      .catch(() => setError(t("loadError")));
  }, [token, t]);

  useEffect(() => {
    if (!token || !instrumentId) return;
    let cancelled = false;
    const key = `${instrumentId}:${timeframe}`;
    const refresh = () => {
      fetchCandles(instrumentId, timeframe)
        .then((response) => {
          if (cancelled) return;
          setData({ key, candles: response.candles });
          setError(null);
        })
        .catch(() => {
          if (!cancelled) setError(t("loadError"));
        });
      fetchPatterns(instrumentId, timeframe)
        .then((response) => {
          if (!cancelled) setPatterns(response.patterns.slice(-4));
        })
        .catch(() => {});
      {
        const to = new Date();
        const from = new Date(
          to.getTime() - VISIBLE_CANDLES * TIMEFRAME_SECONDS[timeframe] * 1000,
        );
        getSmc(instrumentId, timeframe, from, to)
          .then((response) => {
            if (!cancelled) setSmc(response.detections.slice(-4));
          })
          .catch(() => {});
      }
      fetchRsi(instrumentId, timeframe)
        .then((response) => {
          if (cancelled) return;
          const points = response.series["rsi_14"] ?? [];
          setRsi(points.at(-1)?.value ?? null);
        })
        .catch(() => {});
    };
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, instrumentId, timeframe, t]);

  useEffect(() => {
    if (!token || !instrumentId) return;
    const key = `${instrumentId}:${timeframe}`;
    const socket = new WebSocket(marketDataWsUrl(token));
    socket.onopen = () => {
      setLive(true);
      socket.send(
        JSON.stringify({
          type: "subscribe",
          instrument_id: instrumentId,
          timeframe,
        }),
      );
    };
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type !== "candles" || message.timeframe !== timeframe) {
          return;
        }
        setData((current) =>
          current?.key === key
            ? { key, candles: mergeCandles(current.candles, message.candles) }
            : current,
        );
      } catch {
        // Ignore malformed frames.
      }
    };
    socket.onclose = () => setLive(false);
    socket.onerror = () => setLive(false);
    return () => {
      socket.close();
      setLive(false);
    };
  }, [token, instrumentId, timeframe]);

  const overlays = useMemo(
    () => [
      { label: t("sma20"), color: "#38bdf8", points: simpleMovingAverage(candles, 20) },
      { label: t("sma50"), color: "#f59e0b", points: simpleMovingAverage(candles, 50) },
    ],
    [candles, t],
  );

  const lastPrice = candles.at(-1)?.close;
  const selectClass =
    "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <div className="flex items-center gap-4 text-sm text-[var(--muted)]">
            {live && (
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--up)]" />
                {t("live")}
              </span>
            )}
            {rsi !== null && (
              <span>
                {t("rsi")} :{" "}
                <span
                  className={
                    rsi >= 70
                      ? "font-medium text-[var(--down)]"
                      : rsi <= 30
                        ? "font-medium text-[var(--up)]"
                        : "font-medium text-[var(--foreground)]"
                  }
                >
                  {rsi.toFixed(1)}
                </span>
              </span>
            )}
            {lastPrice !== undefined && (
              <span>
                {t("lastPrice")} :{" "}
                <span className="font-medium text-[var(--foreground)]">
                  {lastPrice.toLocaleString("fr-FR")}
                </span>
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            {t("instrument")}
            <select
              value={instrumentId ?? ""}
              onChange={(e) => setInstrumentId(Number(e.target.value))}
              className={selectClass}
            >
              {instruments.map((instrument) => (
                <option key={instrument.id} value={instrument.id}>
                  {instrument.symbol} — {instrument.exchange}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
            {t("timeframe")}
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className={selectClass}
            >
              {TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  {t(`timeframes.${tf}`)}
                </option>
              ))}
            </select>
          </label>

          <p className="flex items-center gap-2 text-sm text-[var(--muted)]">
            {t("indicators")} :
            <span className="text-sky-400">{t("sma20")}</span>
            <span className="text-amber-500">{t("sma50")}</span>
          </p>

          <div className="ml-auto flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1 text-sm">
            <button
              onClick={() => setChartType("candles")}
              className={`rounded-md px-3 py-1 transition-colors ${
                chartType === "candles"
                  ? "bg-white/10 text-[var(--foreground)]"
                  : "text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              {t("chartType.candles")}
            </button>
            <button
              onClick={() => setChartType("area")}
              className={`rounded-md px-3 py-1 transition-colors ${
                chartType === "area"
                  ? "bg-white/10 text-[var(--foreground)]"
                  : "text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              {t("chartType.area")}
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          {loading ? (
            <p className="flex h-[480px] items-center justify-center text-sm text-[var(--muted)]">
              {t("loading")}
            </p>
          ) : error ? (
            <p className="flex h-[480px] items-center justify-center text-sm text-red-400">
              {error}
            </p>
          ) : candles.length === 0 ? (
            <p className="flex h-[480px] items-center justify-center text-sm text-[var(--muted)]">
              {t("empty")}
            </p>
          ) : (
            <CandlestickChart
              candles={candles}
              overlays={overlays}
              chartType={chartType}
              fitKey={dataKey}
            />
          )}
          {chartType === "area" && (
            <p className="mt-2 text-xs text-[var(--muted)]">
              {t("chartType.areaHint")}
            </p>
          )}
        </div>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-[var(--muted)]">
              {t("prediction.title")}
            </h2>
            <button
              onClick={() => {
                if (!instrumentId) return;
                setPredicting(true);
                setPredictionError(false);
                getPrediction(instrumentId, timeframe)
                  .then(setPrediction)
                  .catch(() => setPredictionError(true))
                  .finally(() => setPredicting(false));
              }}
              disabled={predicting || !instrumentId}
              className="brand-button rounded-lg px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {predicting ? t("prediction.analyzing") : t("prediction.analyze")}
            </button>
          </div>
          {predictionError && (
            <p className="text-sm text-red-400">{t("prediction.error")}</p>
          )}
          {prediction && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-[var(--up)]">
                  {t("prediction.probUp")} :{" "}
                  <strong>{(prediction.prob_up * 100).toFixed(1)} %</strong>
                </span>
                <span className="text-[var(--down)]">
                  {t("prediction.probDown")} :{" "}
                  <strong>{(prediction.prob_down * 100).toFixed(1)} %</strong>
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[var(--up)] to-[var(--accent-cyan)]"
                  style={{ width: `${prediction.prob_up * 100}%` }}
                />
              </div>
              <p className="text-xs text-[var(--muted)]">
                {t("prediction.quality")} :{" "}
                {(prediction.test_accuracy * 100).toFixed(1)} % —{" "}
                {t("prediction.baseline")} :{" "}
                {(prediction.baseline_accuracy * 100).toFixed(1)} % —{" "}
                {t("prediction.trainingRows")} : {prediction.training_rows}
              </p>
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--muted)]">
                  {t("prediction.topFeatures")}
                </p>
                <ul className="space-y-1 text-xs">
                  {prediction.top_features.map((f) => (
                    <li key={f.feature} className="flex items-center gap-2">
                      <span
                        className={
                          f.contribution >= 0
                            ? "text-[var(--up)]"
                            : "text-[var(--down)]"
                        }
                      >
                        {f.contribution >= 0 ? "▲" : "▼"}
                      </span>
                      <span>{t(`prediction.featureNames.${f.feature}`)}</span>
                      <span className="text-[var(--muted)]">
                        ({f.contribution >= 0 ? "+" : ""}
                        {f.contribution.toFixed(3)})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-xs text-[var(--muted)]">
                {prediction.explanation}
              </p>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("patternsTitle")}
          </h2>
          {patterns.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noPatterns")}</p>
          ) : (
            <ul className="space-y-2">
              {patterns.map((p, index) => (
                <li
                  key={`${p.pattern}-${p.time}-${index}`}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm"
                >
                  <span
                    className={
                      p.direction === "bullish"
                        ? "font-medium text-[var(--up)]"
                        : "font-medium text-[var(--down)]"
                    }
                  >
                    {t(`patternNames.${p.pattern}`)} (
                    {t(`directions.${p.direction}`)})
                  </span>
                  <span className="text-[var(--muted)]">
                    {new Date(p.time).toLocaleString("fr-FR")} —{" "}
                    {Math.round(p.confidence * 100)} % {t("confidence")}
                  </span>
                  <span className="w-full text-xs text-[var(--muted)]">
                    {p.explanation}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("smcTitle")}
          </h2>
          {smc.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noSmc")}</p>
          ) : (
            <ul className="space-y-2">
              {smc.map((d, index) => (
                <li
                  key={`${d.kind}-${d.time}-${index}`}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm"
                >
                  <span
                    className={
                      d.direction === "bullish"
                        ? "font-medium text-[var(--up)]"
                        : "font-medium text-[var(--down)]"
                    }
                  >
                    {t(`smcKinds.${d.kind}`)} ({t(`directions.${d.direction}`)})
                  </span>
                  <span className="text-[var(--muted)]">
                    {new Date(d.time).toLocaleString("fr-FR")} —{" "}
                    {Math.round(d.confidence * 100)} % {t("confidence")}
                  </span>
                  <span className="w-full text-xs text-[var(--muted)]">
                    {d.explanation}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <p className="text-xs text-[var(--muted)]">{t("autoRefresh")}</p>
      </main>
    </div>
  );
}
