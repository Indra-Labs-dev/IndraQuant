"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { CalibrationChart } from "@/components/charts/CalibrationChart";
import { RollingAccuracyChart } from "@/components/charts/RollingAccuracyChart";
import { AppNav } from "@/components/layout/AppNav";
import {
  getInstruments,
  getPredictionDashboard,
  getSettings,
  getTrainingSessions,
  startTraining,
  stopTraining,
  updateSetting,
} from "@/lib/api-client/client";
import type {
  Instrument,
  PredictionDashboard,
  TrainingSessionInfo,
} from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1s", "5s", "30s", "1m", "5m", "15m", "1h", "4h", "1d"];
const REFRESH_INTERVAL_MS = 30_000;
const PRIORITY_SETTING_KEY = "training_priority_instruments";

function pct(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)} %`;
}

export default function TrainingPage() {
  const t = useTranslations("training");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | "all">("all");
  const [timeframe, setTimeframe] = useState("1h");
  const [dashboard, setDashboard] = useState<PredictionDashboard | null>(null);
  const [sessions, setSessions] = useState<TrainingSessionInfo[]>([]);
  const [priorityIds, setPriorityIds] = useState<Set<number>>(new Set());
  const [priorityLoaded, setPriorityLoaded] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    getInstruments()
      .then((r) => setInstruments(r.instruments))
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token) return;
    getSettings()
      .then((r) => {
        const raw = r.settings[PRIORITY_SETTING_KEY];
        if (raw) {
          try {
            const ids = JSON.parse(raw);
            if (Array.isArray(ids)) setPriorityIds(new Set(ids));
          } catch {
            // Ignore a corrupted stored value — starts from an empty selection.
          }
        }
      })
      .catch(() => {})
      .finally(() => setPriorityLoaded(true));
  }, [token]);

  // Persist the selection only after the initial load completed, so an
  // empty default state never overwrites what was already saved.
  useEffect(() => {
    if (!token || !priorityLoaded) return;
    updateSetting(PRIORITY_SETTING_KEY, JSON.stringify([...priorityIds])).catch(
      () => {},
    );
  }, [token, priorityLoaded, priorityIds]);

  const togglePriority = (id: number) => {
    setPriorityIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const refresh = () =>
      getPredictionDashboard(
        timeframe,
        instrumentId === "all" ? undefined : instrumentId,
        150,
      )
        .then((d) => {
          if (!cancelled) {
            setDashboard(d);
            setError(false);
          }
        })
        .catch(() => {
          if (!cancelled) setError(true);
        });
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, timeframe, instrumentId]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const refresh = () =>
      getTrainingSessions()
        .then((r) => {
          if (!cancelled) setSessions(r.sessions);
        })
        .catch(() => {});
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token]);

  const priorityList = [...priorityIds];
  const runningPriorityCount = sessions.filter(
    (s) => s.timeframe === timeframe && priorityIds.has(s.instrument_id),
  ).length;
  const isRunning = runningPriorityCount > 0;

  const toggleTraining = () => {
    if (priorityList.length === 0) return;
    setToggling(true);
    const call = isRunning
      ? stopTraining(timeframe, priorityList)
      : startTraining(timeframe, priorityList);
    call
      .then((r) => setSessions(r.sessions))
      .catch(() => setError(true))
      .finally(() => setToggling(false));
  };

  const cryptoInstruments = instruments.filter((i) => i.asset_class === "crypto");
  const equityInstruments = instruments.filter((i) => i.asset_class === "equity");

  const selectClass =
    "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";
  const cardClass = "rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3";

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
            {t("timeframe")}
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
            {t("viewFilter")}
            <select
              value={instrumentId}
              onChange={(e) =>
                setInstrumentId(e.target.value === "all" ? "all" : Number(e.target.value))
              }
              className={selectClass}
            >
              <option value="all">{t("allInstruments")}</option>
              {instruments.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.symbol} — {i.exchange}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <p className="text-sm text-red-400">{t("error")}</p>}

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="mb-1 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-medium text-[var(--muted)]">
              {t("prioritySelectionTitle")}
            </h2>
            <button
              onClick={toggleTraining}
              disabled={toggling || priorityList.length === 0}
              className={
                isRunning
                  ? "rounded-lg border border-[var(--down)]/40 px-4 py-2 text-sm font-medium text-[var(--down)] transition-colors hover:bg-[var(--down)]/10 disabled:opacity-50"
                  : "brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
              }
            >
              {toggling
                ? t("toggling")
                : isRunning
                  ? t("stopTraining")
                  : t("startTraining")}
            </button>
          </div>
          <p className="mb-3 text-xs text-[var(--muted)]">{t("prioritySelectionHint")}</p>

          {sessions.length > 0 && (
            <p className="mb-3 text-xs text-[var(--muted)]">
              {t("activeSessions")} :{" "}
              {sessions.map((s) => `${s.symbol} (${s.timeframe})`).join(", ")}
            </p>
          )}

          <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
            {cryptoInstruments.length > 0 && (
              <div className="col-span-full">
                <p className="mb-1.5 text-xs font-medium text-[var(--muted)]">
                  {t("groupCrypto")}
                </p>
                <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
                  {cryptoInstruments.map((i) => (
                    <label
                      key={i.id}
                      className="flex items-center gap-2 text-sm text-[var(--muted)]"
                    >
                      <input
                        type="checkbox"
                        checked={priorityIds.has(i.id)}
                        onChange={() => togglePriority(i.id)}
                        className="accent-[var(--accent)]"
                      />
                      {i.symbol}
                    </label>
                  ))}
                </div>
              </div>
            )}
            {equityInstruments.length > 0 && (
              <div className="col-span-full">
                <p className="mb-1.5 text-xs font-medium text-[var(--muted)]">
                  {t("groupEquity")}
                </p>
                <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4">
                  {equityInstruments.map((i) => (
                    <label
                      key={i.id}
                      className="flex items-center gap-2 text-sm text-[var(--muted)]"
                    >
                      <input
                        type="checkbox"
                        checked={priorityIds.has(i.id)}
                        onChange={() => togglePriority(i.id)}
                        className="accent-[var(--accent)]"
                      />
                      {i.symbol}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("summaryTitle")}
          </h2>
          {!dashboard || dashboard.summary.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noData")}</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {dashboard.summary.map((s) => (
                <div key={s.timeframe} className={cardClass}>
                  <p className="text-xs text-[var(--muted)]">{s.timeframe}</p>
                  <p
                    className={`text-lg font-semibold ${
                      s.accuracy === null
                        ? "text-[var(--foreground)]"
                        : s.accuracy >= 0.5
                          ? "text-[var(--up)]"
                          : "text-[var(--down)]"
                    }`}
                  >
                    {pct(s.accuracy)}
                  </p>
                  <p className="text-xs text-[var(--muted)]">
                    {t("resolvedPending", { resolved: s.resolved, pending: s.pending })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-1 text-sm font-medium text-[var(--muted)]">
            {t("trendTitle", { timeframe })}
          </h2>
          <p className="mb-3 text-xs text-[var(--muted)]">{t("trendHint")}</p>
          {dashboard && dashboard.accuracy_trend.length > 0 ? (
            <RollingAccuracyChart points={dashboard.accuracy_trend} />
          ) : (
            <p className="flex h-[240px] items-center justify-center text-sm text-[var(--muted)]">
              {t("noResolvedYet")}
            </p>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-1 text-sm font-medium text-[var(--muted)]">
            {t("calibrationTitle")}
          </h2>
          <p className="mb-3 text-xs text-[var(--muted)]">{t("calibrationHint")}</p>
          {dashboard && dashboard.calibration.some((b) => b.accuracy !== null) ? (
            <CalibrationChart buckets={dashboard.calibration} />
          ) : (
            <p className="text-sm text-[var(--muted)]">{t("noResolvedYet")}</p>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("recentTitle")}
          </h2>
          {!dashboard || dashboard.recent.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noData")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-[var(--muted)]">
                  <tr>
                    <th className="py-1 pr-4">{t("columnInstrument")}</th>
                    <th className="py-1 pr-4">{t("columnAsOf")}</th>
                    <th className="py-1 pr-4">{t("columnPredicted")}</th>
                    <th className="py-1 pr-4">{t("columnConfidence")}</th>
                    <th className="py-1 pr-4">{t("columnStatus")}</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.recent.map((r) => (
                    <tr key={r.id} className="border-t border-white/5">
                      <td className="py-1.5 pr-4">{r.symbol}</td>
                      <td className="py-1.5 pr-4 text-[var(--muted)]">
                        {new Date(r.as_of).toLocaleString("fr-FR")}
                      </td>
                      <td
                        className={`py-1.5 pr-4 font-medium ${
                          r.predicted_direction === "up"
                            ? "text-[var(--up)]"
                            : "text-[var(--down)]"
                        }`}
                      >
                        {r.predicted_direction === "up" ? "▲ hausse" : "▼ baisse"}
                      </td>
                      <td className="py-1.5 pr-4">
                        {(Math.max(r.raw_prob_up, 1 - r.raw_prob_up) * 100).toFixed(1)} %
                      </td>
                      <td className="py-1.5 pr-4">
                        {r.resolved_at === null ? (
                          <span className="text-[var(--accent-orange)]">
                            {t("statusPending")}
                          </span>
                        ) : r.correct ? (
                          <span className="text-[var(--up)]">
                            {t("statusCorrect")}
                          </span>
                        ) : (
                          <span className="text-[var(--down)]">
                            {t("statusIncorrect")}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <p className="text-xs text-[var(--muted)]">{t("refreshHint")}</p>
      </main>
    </div>
  );
}
