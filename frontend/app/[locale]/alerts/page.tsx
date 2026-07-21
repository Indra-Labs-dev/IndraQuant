"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import {
  createAlert,
  deleteAlert,
  getInstruments,
  listAlerts,
} from "@/lib/api-client/client";
import type { Alert, AlertConditionType, Instrument } from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];
const CONDITIONS: AlertConditionType[] = [
  "price_above",
  "price_below",
  "rsi_above",
  "rsi_below",
];
const REFRESH_INTERVAL_MS = 15_000;

export default function AlertsPage() {
  const t = useTranslations("alerts");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [instrumentId, setInstrumentId] = useState<number | null>(null);
  const [timeframe, setTimeframe] = useState("1m");
  const [condition, setCondition] = useState<AlertConditionType>("price_above");
  const [threshold, setThreshold] = useState(0);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(false);

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
  }, [token]);

  useEffect(() => {
    if (!token) return;
    const refresh = () => listAlerts().then((r) => setAlerts(r.alerts)).catch(() => {});
    refresh();
    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [token]);

  const create = () => {
    if (!instrumentId) return;
    setCreating(true);
    setError(false);
    createAlert({ instrument_id: instrumentId, timeframe, condition_type: condition, threshold })
      .then(() => listAlerts())
      .then((r) => setAlerts(r.alerts))
      .catch(() => setError(true))
      .finally(() => setCreating(false));
  };

  const remove = (id: number) => {
    deleteAlert(id)
      .then(() => listAlerts())
      .then((r) => setAlerts(r.alerts))
      .catch(() => {});
  };

  const symbolFor = (id: number) =>
    instruments.find((i) => i.id === id)?.symbol ?? `#${id}`;

  const inputClass =
    "w-28 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";
  const selectClass =
    "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <div className="flex flex-wrap items-end gap-4 text-sm text-[var(--muted)]">
          <label className="flex flex-col gap-1">
            {t("instrument")}
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
            {t("condition")}
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value as AlertConditionType)}
              className={selectClass}
            >
              {CONDITIONS.map((c) => (
                <option key={c} value={c}>
                  {t(`conditions.${c}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            {t("threshold")}
            <input
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className={inputClass}
            />
          </label>
          <button
            onClick={create}
            disabled={creating || !instrumentId}
            className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {creating ? t("creating") : t("create")}
          </button>
        </div>

        {error && <p className="text-sm text-red-400">{t("error")}</p>}

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("list")}
          </h2>
          {alerts.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noAlerts")}</p>
          ) : (
            <ul className="space-y-2">
              {alerts.map((alert) => (
                <li
                  key={alert.id}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm"
                >
                  <span
                    className={
                      alert.is_active
                        ? "text-[var(--foreground)]"
                        : "text-[var(--muted)]"
                    }
                  >
                    {symbolFor(alert.instrument_id)} —{" "}
                    {t(`conditions.${alert.condition_type}`)} {alert.threshold}{" "}
                    ({alert.timeframe})
                  </span>
                  <span
                    className={
                      alert.is_active ? "text-[var(--up)]" : "text-[var(--accent-orange)]"
                    }
                  >
                    {alert.is_active ? t("statusActive") : t("statusTriggered")}
                  </span>
                  <button
                    onClick={() => remove(alert.id)}
                    className="rounded-md border border-white/15 px-2 py-0.5 text-xs text-[var(--muted)] transition-colors hover:text-[var(--down)]"
                  >
                    {t("delete")}
                  </button>
                  {alert.message && (
                    <span className="w-full text-xs text-[var(--muted)]">
                      {alert.message}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
