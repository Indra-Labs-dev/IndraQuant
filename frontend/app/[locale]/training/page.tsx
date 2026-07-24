"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { CalibrationChart } from "@/components/charts/CalibrationChart";
import { RollingAccuracyChart } from "@/components/charts/RollingAccuracyChart";
import { AppNav } from "@/components/layout/AppNav";
import {
  getDriftReport,
  getInstruments,
  getModelRegistry,
  getModelValidation,
  getPredictionDashboard,
  getSettings,
  getTrainingSessions,
  runModelAbTest,
  startTraining,
  stopTraining,
  updateSetting,
} from "@/lib/api-client/client";
import type {
  AbTestResult,
  DriftReport,
  Instrument,
  ModelRegistry,
  ModelValidation,
  PredictionDashboard,
  TrainingSessionInfo,
} from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1s", "5s", "30s", "1m", "5m", "15m", "1h", "4h", "1d"];
const REFRESH_INTERVAL_MS = 30_000;
const PRIORITY_SETTING_KEY = "training_priority_instruments";
const RECENT_FETCH_LIMIT = 300;
const RECENT_PAGE_SIZE = 20;

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
  const [recentPage, setRecentPage] = useState(0);
  const [drift, setDrift] = useState<DriftReport | null>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [driftError, setDriftError] = useState(false);
  const [modelValidation, setModelValidation] = useState<ModelValidation | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState(false);
  const [modelRegistry, setModelRegistry] = useState<ModelRegistry | null>(null);
  const [registryLoading, setRegistryLoading] = useState(false);
  const [registryError, setRegistryError] = useState(false);
  const [abTest, setAbTest] = useState<AbTestResult | null>(null);
  const [abTestLoading, setAbTestLoading] = useState(false);
  const [abTestError, setAbTestError] = useState(false);

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
        RECENT_FETCH_LIMIT,
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

  // Reset pagination when the underlying dataset changes — adjusting state
  // during render (not in an effect) per React's guidance for this exact
  // "reset on prop change" case.
  const recentFilterKey = `${timeframe}:${instrumentId}`;
  const [lastRecentFilterKey, setLastRecentFilterKey] = useState(recentFilterKey);
  if (recentFilterKey !== lastRecentFilterKey) {
    setLastRecentFilterKey(recentFilterKey);
    setRecentPage(0);
  }

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

  const recentTotal = dashboard?.recent.length ?? 0;
  const recentPageCount = Math.max(1, Math.ceil(recentTotal / RECENT_PAGE_SIZE));
  const recentPageClamped = Math.min(recentPage, recentPageCount - 1);
  const recentPageRows = (dashboard?.recent ?? []).slice(
    recentPageClamped * RECENT_PAGE_SIZE,
    (recentPageClamped + 1) * RECENT_PAGE_SIZE,
  );

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
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-medium text-[var(--muted)]">
              {t("recentTitle")}
            </h2>
            {recentTotal > 0 && (
              <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
                <button
                  onClick={() => setRecentPage((p) => Math.max(0, p - 1))}
                  disabled={recentPageClamped === 0}
                  className="rounded-md border border-white/10 px-2 py-1 transition-colors hover:text-[var(--foreground)] disabled:opacity-30"
                >
                  {t("previousPage")}
                </button>
                <span>
                  {t("pageIndicator", {
                    page: recentPageClamped + 1,
                    total: recentPageCount,
                  })}
                </span>
                <button
                  onClick={() =>
                    setRecentPage((p) => Math.min(recentPageCount - 1, p + 1))
                  }
                  disabled={recentPageClamped >= recentPageCount - 1}
                  className="rounded-md border border-white/10 px-2 py-1 transition-colors hover:text-[var(--foreground)] disabled:opacity-30"
                >
                  {t("nextPage")}
                </button>
              </div>
            )}
          </div>
          {!dashboard || recentTotal === 0 ? (
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
                  {recentPageRows.map((r) => (
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

        {instrumentId !== "all" && (
          <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-[var(--muted)]">
                {t("driftTitle")}
              </h2>
              <button
                onClick={() => {
                  setDriftLoading(true);
                  setDriftError(false);
                  getDriftReport(instrumentId, timeframe)
                    .then(setDrift)
                    .catch(() => setDriftError(true))
                    .finally(() => setDriftLoading(false));
                }}
                disabled={driftLoading}
                className="brand-button rounded-lg px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {driftLoading ? t("driftChecking") : t("driftCheck")}
              </button>
            </div>
            {driftError && <p className="text-sm text-red-400">{t("driftError")}</p>}
            {drift && (
              <div className="space-y-3 text-sm">
                <p>
                  {t("driftOverall")} :{" "}
                  <span
                    className={
                      drift.overall_severity === "significative"
                        ? "font-medium text-[var(--down)]"
                        : drift.overall_severity === "modérée"
                          ? "font-medium text-[var(--accent-orange)]"
                          : "font-medium text-[var(--up)]"
                    }
                  >
                    {t(`driftSeverity.${drift.overall_severity}`)}
                  </span>
                </p>
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs">
                  <p className="mb-1 font-medium text-[var(--muted)]">
                    {t("driftDataTitle")}
                  </p>
                  <ul className="space-y-1">
                    {drift.feature_drifts.map((f) => (
                      <li key={f.feature} className="flex items-center justify-between gap-2">
                        <span>{f.feature}</span>
                        <span className="text-[var(--muted)]">
                          {f.psi === null ? "—" : `PSI ${f.psi.toFixed(3)}`} —{" "}
                          {t(`driftSeverity.${f.severity}`)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs">
                  <p className="mb-1 font-medium text-[var(--muted)]">
                    {t("driftLabelTitle")}
                  </p>
                  <p className="text-[var(--muted)]">{drift.label_drift.explanation}</p>
                </div>
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs">
                  <p className="mb-1 font-medium text-[var(--muted)]">
                    {t("driftConceptTitle")}
                  </p>
                  <p className="text-[var(--muted)]">{drift.concept_drift.explanation}</p>
                </div>
              </div>
            )}
          </section>
        )}

        {instrumentId !== "all" && (
          <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-[var(--muted)]">
                {t("validationTitle")}
              </h2>
              <button
                onClick={() => {
                  setValidationLoading(true);
                  setValidationError(false);
                  getModelValidation(instrumentId, timeframe)
                    .then(setModelValidation)
                    .catch(() => setValidationError(true))
                    .finally(() => setValidationLoading(false));
                }}
                disabled={validationLoading}
                className="brand-button rounded-lg px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {validationLoading ? t("validationChecking") : t("validationCheck")}
              </button>
            </div>
            {validationError && (
              <p className="text-sm text-red-400">{t("validationError")}</p>
            )}
            {modelValidation && (
              <div className="space-y-2 text-xs">
                <p className="text-[var(--muted)]">
                  {t("validationNaive")} :{" "}
                  <span className="text-[var(--foreground)]">
                    {modelValidation.naive_split_accuracy === null
                      ? "—"
                      : `${(modelValidation.naive_split_accuracy * 100).toFixed(1)} %`}
                  </span>
                </p>
                {[
                  modelValidation.time_series_cv,
                  modelValidation.purged_embargo_cv,
                  modelValidation.nested_cv,
                ].map((summary) => (
                  <div
                    key={summary.method}
                    className="rounded-lg border border-white/10 bg-white/[0.02] p-3"
                  >
                    <p className="mb-1 font-medium text-[var(--muted)]">{summary.method}</p>
                    <p className="text-[var(--muted)]">{summary.explanation}</p>
                  </div>
                ))}
                <p className="text-[var(--muted)]">{modelValidation.explanation}</p>
              </div>
            )}
          </section>
        )}

        {instrumentId !== "all" && (
          <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-[var(--muted)]">
                {t("registryTitle")}
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setAbTestLoading(true);
                    setAbTestError(false);
                    runModelAbTest(instrumentId, timeframe)
                      .then(setAbTest)
                      .catch(() => setAbTestError(true))
                      .finally(() => setAbTestLoading(false));
                  }}
                  disabled={abTestLoading}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {abTestLoading ? t("registryAbTesting") : t("registryAbTest")}
                </button>
                <button
                  onClick={() => {
                    setRegistryLoading(true);
                    setRegistryError(false);
                    getModelRegistry(instrumentId, timeframe)
                      .then(setModelRegistry)
                      .catch(() => setRegistryError(true))
                      .finally(() => setRegistryLoading(false));
                  }}
                  disabled={registryLoading}
                  className="brand-button rounded-lg px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {registryLoading ? t("registryChecking") : t("registryCheck")}
                </button>
              </div>
            </div>
            {registryError && (
              <p className="text-sm text-red-400">{t("registryError")}</p>
            )}
            {abTestError && (
              <p className="text-sm text-red-400">{t("registryAbTestError")}</p>
            )}
            {abTest && (
              <div className="mb-3 rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs">
                <p className="mb-1 font-medium text-[var(--muted)]">
                  {t("registryAbTestTitle")}
                </p>
                <p className="text-[var(--muted)]">{abTest.explanation}</p>
              </div>
            )}
            {modelRegistry && (
              <div className="space-y-2">
                <p className="text-xs text-[var(--muted)]">{modelRegistry.explanation}</p>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-[var(--muted)]">
                      <th className="py-1.5 pr-4">{t("registryVersion")}</th>
                      <th className="py-1.5 pr-4">{t("registryChampionType")}</th>
                      <th className="py-1.5 pr-4">XGBoost</th>
                      <th className="py-1.5 pr-4">Régression logistique</th>
                      <th className="py-1.5 pr-4">{t("registryStatus")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelRegistry.versions.map((v) => (
                      <tr key={v.version} className="border-b border-white/5">
                        <td className="py-1.5 pr-4">{v.version}</td>
                        <td className="py-1.5 pr-4">{v.champion_model_type}</td>
                        <td className="py-1.5 pr-4">
                          {(v.xgboost_accuracy * 100).toFixed(1)} %
                        </td>
                        <td className="py-1.5 pr-4">
                          {(v.logistic_regression_accuracy * 100).toFixed(1)} %
                        </td>
                        <td className="py-1.5 pr-4">
                          {v.is_champion ? (
                            <span className="text-[var(--up)]">{t("registryChampion")}</span>
                          ) : v.rolled_back ? (
                            <span className="text-[var(--down)]">
                              {t("registryRolledBack")}
                            </span>
                          ) : (
                            <span className="text-[var(--muted)]">
                              {t("registryChallenger")}
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
        )}

        <p className="text-xs text-[var(--muted)]">{t("refreshHint")}</p>
      </main>
    </div>
  );
}
