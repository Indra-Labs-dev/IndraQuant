"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { EquityChart } from "@/components/charts/EquityChart";
import { AppNav } from "@/components/layout/AppNav";
import { StrategyFields } from "@/components/strategy/StrategyFields";
import {
  getInstruments,
  listBacktests,
  listStrategies,
  runBacktest,
  runWalkForward,
} from "@/lib/api-client/client";
import type {
  BacktestReport,
  BacktestSummary,
  Instrument,
  StrategyDefinition,
  StrategySpec,
  WalkForwardReport,
} from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

function pct(value: number): string {
  return `${(value * 100).toFixed(2)} %`;
}

function strategySummary(strategy: StrategySpec): string {
  if (strategy.type === "rsi_reversion") {
    return `RSI ${strategy.period} (${strategy.low}/${strategy.high})`;
  }
  if (strategy.type === "macd_crossover") {
    return `MACD ${strategy.fast}/${strategy.slow}/${strategy.signal}`;
  }
  if (strategy.type === "bollinger_breakout") {
    return `Bollinger ${strategy.period} (${strategy.num_std}σ)`;
  }
  return `MM ${strategy.fast}/${strategy.slow}`;
}

export default function BacktestingPage() {
  const t = useTranslations("backtest");
  const tc = useTranslations("common");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | null>(null);
  const [timeframe, setTimeframe] = useState("1h");
  const [days, setDays] = useState(60);
  const [strategies, setStrategies] = useState<StrategyDefinition[]>([]);
  const [strategyType, setStrategyType] = useState("sma_crossover");
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({
    fast: 20,
    slow: 50,
  });
  const [capital, setCapital] = useState(10000);
  const [report, setReport] = useState<BacktestReport | null>(null);
  const [walkForward, setWalkForward] = useState<WalkForwardReport | null>(null);
  const [history, setHistory] = useState<BacktestSummary[]>([]);
  const [busy, setBusy] = useState<"backtest" | "walkforward" | null>(null);
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
    listBacktests()
      .then((r) => setHistory(r.backtests))
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

  const params = () => ({
    instrument_id: instrumentId!,
    timeframe,
    from: new Date(Date.now() - days * 86_400_000),
    to: new Date(),
    strategy: { type: strategyType, ...strategyParams },
    initial_capital: capital,
  });

  const launch = () => {
    if (!instrumentId) return;
    setBusy("backtest");
    setError(null);
    setWalkForward(null);
    runBacktest(params())
      .then((r) => {
        setReport(r);
        return listBacktests();
      })
      .then((r) => setHistory(r.backtests))
      .catch((e) => setError(e?.message ?? tc("error")))
      .finally(() => setBusy(null));
  };

  const launchWalkForward = () => {
    if (!instrumentId) return;
    setBusy("walkforward");
    setError(null);
    runWalkForward({ ...params(), folds: 4 })
      .then(setWalkForward)
      .catch((e) => setError(e?.message ?? tc("error")))
      .finally(() => setBusy(null));
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
          <label className="flex flex-col gap-1">
            {tc("days")}
            <input
              type="number"
              min={7}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className={inputClass}
            />
          </label>
          <StrategyFields
            definitions={strategies}
            type={strategyType}
            onTypeChange={setStrategyType}
            params={strategyParams}
            onParamsChange={setStrategyParams}
            label={t("strategy")}
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
            onClick={launch}
            disabled={busy !== null}
            className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {busy === "backtest" ? tc("running") : tc("run")}
          </button>
          <button
            onClick={launchWalkForward}
            disabled={busy !== null}
            className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-[var(--foreground)] transition-colors hover:bg-white/5 disabled:opacity-50"
          >
            {busy === "walkforward" ? t("walkForwardRunning") : t("walkForward")}
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {report && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("finalEquity")}</p>
                <p className="text-lg font-semibold">
                  {report.final_equity.toLocaleString("fr-FR")}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("totalReturn")}</p>
                <p
                  className={`text-lg font-semibold ${report.total_return >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                >
                  {pct(report.total_return)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("maxDrawdown")}</p>
                <p className="text-lg font-semibold text-[var(--down)]">
                  {pct(report.max_drawdown)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("sharpe")}</p>
                <p className="text-lg font-semibold">
                  {report.sharpe?.toFixed(2) ?? "n/d"}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("winRate")}</p>
                <p className="text-lg font-semibold">
                  {report.win_rate !== null ? pct(report.win_rate) : "n/d"}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("trades")}</p>
                <p className="text-lg font-semibold">{report.trade_count}</p>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                {t("equityCurve")}
              </h2>
              <EquityChart points={report.equity_curve} />
            </div>

            <p className="text-sm text-[var(--muted)]">{report.explanation}</p>
          </>
        )}

        {walkForward && (
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
              {t("walkForward")}
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-[var(--muted)]">
                  <tr>
                    <th className="py-1 pr-4">{t("fold")}</th>
                    <th className="py-1 pr-4">{t("bestParams")}</th>
                    <th className="py-1 pr-4">{t("trainReturn")}</th>
                    <th className="py-1 pr-4">{t("testReturn")}</th>
                  </tr>
                </thead>
                <tbody>
                  {walkForward.folds.map((f) => (
                    <tr key={f.fold} className="border-t border-white/5">
                      <td className="py-1.5 pr-4">{f.fold}</td>
                      <td className="py-1.5 pr-4">
                        MM {f.best_fast}/{f.best_slow}
                      </td>
                      <td className="py-1.5 pr-4">{pct(f.train_return)}</td>
                      <td
                        className={`py-1.5 pr-4 ${f.test_return >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                      >
                        {pct(f.test_return)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-sm text-[var(--muted)]">
              {t("meanTest")} : {pct(walkForward.mean_test_return)} —{" "}
              {t("positiveFolds")} : {walkForward.positive_test_folds}/
              {walkForward.total_folds}
            </p>
            <p className="mt-2 text-xs text-[var(--muted)]">
              {walkForward.explanation}
            </p>
          </div>
        )}

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("history")}
          </h2>
          {history.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noHistory")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-[var(--muted)]">
                  <tr>
                    <th className="py-1 pr-4">#</th>
                    <th className="py-1 pr-4">{tc("timeframe")}</th>
                    <th className="py-1 pr-4">{t("strategy")}</th>
                    <th className="py-1 pr-4">{t("totalReturn")}</th>
                    <th className="py-1 pr-4">{t("maxDrawdown")}</th>
                    <th className="py-1 pr-4">{t("trades")}</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id} className="border-t border-white/5">
                      <td className="py-1.5 pr-4">{h.id}</td>
                      <td className="py-1.5 pr-4">{h.timeframe}</td>
                      <td className="py-1.5 pr-4">
                        {strategySummary(h.strategy)}
                      </td>
                      <td
                        className={`py-1.5 pr-4 ${h.total_return >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                      >
                        {pct(h.total_return)}
                      </td>
                      <td className="py-1.5 pr-4">{pct(h.max_drawdown)}</td>
                      <td className="py-1.5 pr-4">{h.trade_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
