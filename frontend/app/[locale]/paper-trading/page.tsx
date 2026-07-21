"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { StrategyFields } from "@/components/strategy/StrategyFields";
import {
  createPaperSession,
  getInstruments,
  getPaperSession,
  listPaperSessions,
  listStrategies,
  stopPaperSession,
} from "@/lib/api-client/client";
import type {
  Instrument,
  PaperSession,
  PaperSessionDetail,
  StrategyDefinition,
  StrategySpec,
} from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1s", "5s", "30s", "1m", "5m", "15m", "1h"];
const DETAIL_REFRESH_MS = 10_000;

function pct(value: number): string {
  return `${(value * 100).toFixed(2)} %`;
}

function strategySummary(strategy: StrategySpec): string {
  if (strategy.type === "rsi_reversion") {
    return `RSI ${strategy.period} (${strategy.low}/${strategy.high})`;
  }
  return `MM ${strategy.fast}/${strategy.slow}`;
}

export default function PaperTradingPage() {
  const t = useTranslations("paper");
  const tc = useTranslations("common");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | null>(null);
  const [timeframe, setTimeframe] = useState("1m");
  const [strategies, setStrategies] = useState<StrategyDefinition[]>([]);
  const [strategyType, setStrategyType] = useState("sma_crossover");
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({
    fast: 10,
    slow: 30,
  });
  const [capital, setCapital] = useState(10000);
  const [sessions, setSessions] = useState<PaperSession[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PaperSessionDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    getInstruments()
      .then((r) => {
        setInstruments(r.instruments);
        setInstrumentId((cur) => cur ?? r.instruments[0]?.id ?? null);
      })
      .catch(() => {});
    listPaperSessions()
      .then((r) => {
        setSessions(r.sessions);
        setSelectedId((cur) => cur ?? r.sessions[0]?.id ?? null);
      })
      .catch(() => {});
    listStrategies()
      .then((r) => {
        setStrategies(r.strategies);
        const first = r.strategies[0];
        if (first) {
          setStrategyType(first.type);
          setStrategyParams(
            Object.fromEntries(first.parameters.map((p) => [p.name, p.default])),
          );
        }
      })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token || selectedId === null) return;
    let cancelled = false;
    const refresh = () =>
      getPaperSession(selectedId)
        .then((d) => {
          if (!cancelled) setDetail(d);
        })
        .catch(() => {});
    refresh();
    const interval = setInterval(refresh, DETAIL_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, selectedId]);

  const start = () => {
    if (!instrumentId) return;
    setBusy(true);
    setError(null);
    createPaperSession({
      instrument_id: instrumentId,
      timeframe,
      strategy: { type: strategyType, ...strategyParams },
      initial_capital: capital,
    })
      .then((session) => {
        setSelectedId(session.id);
        return listPaperSessions();
      })
      .then((r) => setSessions(r.sessions))
      .catch((e) => setError(e?.message ?? tc("error")))
      .finally(() => setBusy(false));
  };

  const stop = (id: number) => {
    stopPaperSession(id)
      .then(() => listPaperSessions())
      .then((r) => setSessions(r.sessions))
      .catch(() => {});
  };

  const inputClass =
    "w-24 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";
  const selectClass =
    "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";
  const cardClass =
    "rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3";

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <div className="flex flex-wrap items-end gap-4 text-sm text-[var(--muted)]">
          <label className="flex flex-col gap-1">
            {tc("instrument")}
            <select
              value={instrumentId ?? ""}
              onChange={(e) => setInstrumentId(Number(e.target.value))}
              className={selectClass}
            >
              {instruments.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.symbol} — {i.exchange}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            {tc("timeframe")}
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className={selectClass}
            >
              {TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </label>
          <StrategyFields
            definitions={strategies}
            type={strategyType}
            onTypeChange={setStrategyType}
            params={strategyParams}
            onParamsChange={setStrategyParams}
            label={tc("strategy")}
          />
          <label className="flex flex-col gap-1">
            {tc("capital")}
            <input
              type="number"
              min={100}
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className={inputClass}
            />
          </label>
          <button
            onClick={start}
            disabled={busy}
            className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {busy ? t("starting") : t("start")}
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("sessions")}
          </h2>
          {sessions.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noSessions")}</p>
          ) : (
            <ul className="space-y-1.5">
              {sessions.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center gap-3 text-sm">
                  <button
                    onClick={() => setSelectedId(s.id)}
                    className={`rounded-md px-2 py-1 transition-colors ${
                      selectedId === s.id
                        ? "bg-white/10 text-[var(--foreground)]"
                        : "text-[var(--muted)] hover:text-[var(--foreground)]"
                    }`}
                  >
                    #{s.id} — {s.timeframe} — {strategySummary(s.strategy)}
                  </button>
                  <span
                    className={
                      s.status === "running"
                        ? "text-[var(--up)]"
                        : "text-[var(--muted)]"
                    }
                  >
                    {s.status === "running"
                      ? t("statusRunning")
                      : t("statusStopped")}
                  </span>
                  {s.status === "running" && (
                    <button
                      onClick={() => stop(s.id)}
                      className="rounded-md border border-white/15 px-2 py-0.5 text-xs text-[var(--muted)] transition-colors hover:text-[var(--down)]"
                    >
                      {t("stop")}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {detail && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("equity")}</p>
                <p className="text-lg font-semibold">
                  {detail.analytics.equity.toLocaleString("fr-FR", {
                    maximumFractionDigits: 2,
                  })}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("pnl")}</p>
                <p
                  className={`text-lg font-semibold ${detail.analytics.pnl >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                >
                  {detail.analytics.pnl.toFixed(2)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("return")}</p>
                <p
                  className={`text-lg font-semibold ${detail.analytics.return_pct >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                >
                  {pct(detail.analytics.return_pct)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("position")}</p>
                <p className="text-lg font-semibold">
                  {detail.analytics.position_quantity.toFixed(6)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("fees")}</p>
                <p className="text-lg font-semibold">
                  {detail.analytics.fees_paid.toFixed(2)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("var")}</p>
                <p className="text-lg font-semibold">
                  {detail.risk.var_95 !== null
                    ? pct(detail.risk.var_95)
                    : t("varNa")}
                </p>
              </div>
            </div>

            <p className="text-xs text-[var(--muted)]">
              {t("maxDrawdown")} : {pct(detail.risk.max_drawdown)} —{" "}
              {detail.risk.explanation}
            </p>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                {t("trades")}
              </h2>
              {detail.trades.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">{t("noTrades")}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <tbody>
                      {detail.trades
                        .slice(-15)
                        .reverse()
                        .map((trade, index) => (
                          <tr key={index} className="border-t border-white/5">
                            <td
                              className={`py-1.5 pr-4 font-medium ${trade.side === "buy" ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                            >
                              {trade.side === "buy" ? "Achat" : "Vente"}
                            </td>
                            <td className="py-1.5 pr-4">
                              {trade.quantity.toFixed(6)}
                            </td>
                            <td className="py-1.5 pr-4">
                              {trade.price.toLocaleString("fr-FR")}
                            </td>
                            <td className="py-1.5 pr-4 text-[var(--muted)]">
                              {trade.executed_at
                                ? new Date(trade.executed_at).toLocaleString(
                                    "fr-FR",
                                  )
                                : ""}
                            </td>
                            <td className="py-1.5 text-xs text-[var(--muted)]">
                              {trade.reason}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <p className="text-xs text-[var(--muted)]">{t("refresh")}</p>
          </>
        )}
      </main>
    </div>
  );
}
