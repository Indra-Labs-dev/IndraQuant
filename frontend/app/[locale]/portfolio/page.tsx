"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import {
  getExposureReport,
  getPortfolioSummary,
  getRiskBudget,
} from "@/lib/api-client/client";
import type {
  ExposureReport,
  PortfolioSummary,
  RiskBudget,
} from "@/lib/api-client/types";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const REFRESH_MS = 15_000;

function pct(value: number): string {
  return `${(value * 100).toFixed(2)} %`;
}

function money(value: number): string {
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

export default function PortfolioPage() {
  const t = useTranslations("portfolio");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [exposure, setExposure] = useState<ExposureReport | null>(null);
  const [riskBudget, setRiskBudget] = useState<RiskBudget | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const refresh = () =>
      getPortfolioSummary()
        .then((data) => {
          if (!cancelled) {
            setSummary(data);
            setError(null);
          }
        })
        .catch((e) => {
          if (!cancelled) setError(e?.message ?? t("error"));
        });
    refresh();
    const interval = setInterval(refresh, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, t]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const refresh = () => {
      getExposureReport()
        .then((r) => {
          if (!cancelled) setExposure(r);
        })
        .catch(() => {});
      getRiskBudget()
        .then((r) => {
          if (!cancelled) setRiskBudget(r);
        })
        .catch(() => {});
    };
    refresh();
    const interval = setInterval(refresh, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token]);

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

        {error && <p className="text-sm text-red-400">{error}</p>}

        {!summary ? (
          <p className="text-sm text-[var(--muted)]">{t("loading")}</p>
        ) : summary.sessions.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">{t("noSessions")}</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("totalEquity")}</p>
                <p className="text-lg font-semibold">{money(summary.total_equity)}</p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("totalPnl")}</p>
                <p
                  className={`text-lg font-semibold ${summary.total_pnl >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                >
                  {money(summary.total_pnl)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("totalReturn")}</p>
                <p
                  className={`text-lg font-semibold ${summary.total_return_pct >= 0 ? "text-[var(--up)]" : "text-[var(--down)]"}`}
                >
                  {pct(summary.total_return_pct)}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("totalFees")}</p>
                <p className="text-lg font-semibold">{money(summary.total_fees)}</p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("runningSessions")}</p>
                <p className="text-lg font-semibold text-[var(--up)]">
                  {summary.running_sessions}
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-[var(--muted)]">{t("stoppedSessions")}</p>
                <p className="text-lg font-semibold text-[var(--muted)]">
                  {summary.stopped_sessions}
                </p>
              </div>
            </div>

            <p className="text-xs text-[var(--muted)]">{summary.explanation}</p>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                {t("allocationTitle")}
              </h2>
              <div className="space-y-2">
                {summary.allocation.map((item) => (
                  <div key={item.instrument_id} className="flex items-center gap-3">
                    <span className="w-28 shrink-0 text-sm font-medium">
                      {item.symbol}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
                      <div
                        className="h-full rounded-full brand-button"
                        style={{ width: `${Math.min(item.weight_pct, 100)}%` }}
                      />
                    </div>
                    <span className="w-16 shrink-0 text-right text-xs text-[var(--muted)]">
                      {item.weight_pct.toFixed(1)} %
                    </span>
                    <span className="w-24 shrink-0 text-right text-xs text-[var(--muted)]">
                      {money(item.equity)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                {t("sessionsTitle")}
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <tbody>
                    {summary.sessions.map((s) => (
                      <tr key={s.id} className="border-t border-white/5">
                        <td className="py-1.5 pr-4">
                          <Link
                            href="/paper-trading"
                            className="text-[var(--foreground)] hover:underline"
                          >
                            #{s.id}
                          </Link>
                        </td>
                        <td className="py-1.5 pr-4 text-[var(--muted)]">
                          {s.timeframe}
                        </td>
                        <td className="py-1.5 pr-4">
                          {s.initial_capital.toLocaleString("fr-FR")}
                        </td>
                        <td
                          className={`py-1.5 pr-4 ${
                            s.status === "running"
                              ? "text-[var(--up)]"
                              : "text-[var(--muted)]"
                          }`}
                        >
                          {s.status === "running"
                            ? t("statusRunning")
                            : t("statusStopped")}
                        </td>
                        <td className="py-1.5 text-xs text-[var(--muted)]">
                          {new Date(s.started_at).toLocaleString("fr-FR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {exposure && (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                  {t("exposureTitle")}
                </h2>
                {exposure.warnings.length === 0 ? (
                  <p className="text-sm text-[var(--up)]">{t("exposureOk")}</p>
                ) : (
                  <ul className="space-y-1 text-sm text-[var(--accent-orange)]">
                    {exposure.warnings.map((w, i) => (
                      <li key={`${w.instrument}-${i}`}>{w.message}</li>
                    ))}
                  </ul>
                )}
                <p className="mt-2 text-xs text-[var(--muted)]">{exposure.explanation}</p>
              </div>
            )}

            {riskBudget && riskBudget.items.length > 0 && (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
                  {t("riskBudgetTitle")}
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs text-[var(--muted)]">
                      <tr>
                        <th className="py-1 pr-4">{t("columnInstrument")}</th>
                        <th className="py-1 pr-4">{t("columnCurrentWeight")}</th>
                        <th className="py-1 pr-4">{t("columnTargetWeight")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskBudget.items.map((item) => (
                        <tr key={item.instrument_id} className="border-t border-white/5">
                          <td className="py-1.5 pr-4">{item.symbol}</td>
                          <td className="py-1.5 pr-4">
                            {item.current_weight_pct.toFixed(1)} %
                          </td>
                          <td className="py-1.5 pr-4">
                            {item.target_weight_pct.toFixed(1)} %
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">{riskBudget.explanation}</p>
              </div>
            )}

            <p className="text-xs text-[var(--muted)]">{t("refresh")}</p>
          </>
        )}
      </main>
    </div>
  );
}
