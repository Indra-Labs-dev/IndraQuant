"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { AppNav } from "@/components/layout/AppNav";
import { getInstruments, getOhlcv } from "@/lib/api-client/client";
import type { Candle, Instrument } from "@/lib/api-client/types";
import { simpleMovingAverage } from "@/lib/indicators";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
const TIMEFRAME_SECONDS: Record<string, number> = {
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

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | null>(null);
  const [timeframe, setTimeframe] = useState<string>("1h");
  const [data, setData] = useState<{ key: string; candles: Candle[] } | null>(
    null,
  );
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
    const refresh = () =>
      fetchCandles(instrumentId, timeframe)
        .then((response) => {
          if (cancelled) return;
          setData({ key, candles: response.candles });
          setError(null);
        })
        .catch(() => {
          if (!cancelled) setError(t("loadError"));
        });
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, instrumentId, timeframe, t]);

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
          {lastPrice !== undefined && (
            <p className="text-sm text-[var(--muted)]">
              {t("lastPrice")} :{" "}
              <span className="font-medium text-[var(--foreground)]">
                {lastPrice.toLocaleString("fr-FR")}
              </span>
            </p>
          )}
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
            <CandlestickChart candles={candles} overlays={overlays} />
          )}
        </div>

        <p className="text-xs text-[var(--muted)]">{t("autoRefresh")}</p>
      </main>
    </div>
  );
}
