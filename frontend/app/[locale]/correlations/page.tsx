"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { getCorrelations, getInstruments } from "@/lib/api-client/client";
import type { CorrelationMatrix, Instrument } from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

function correlationColor(value: number | null): string {
  if (value === null) return "text-[var(--muted)]";
  if (value >= 0.3) return "text-[var(--up)]";
  if (value <= -0.3) return "text-[var(--down)]";
  return "text-[var(--foreground)]";
}

function fmt(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

export default function CorrelationsPage() {
  const t = useTranslations("correlations");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [timeframe, setTimeframe] = useState("1h");
  const [window, setWindowSize] = useState(20);
  const [matrix, setMatrix] = useState<CorrelationMatrix | null>(null);
  const [loading, setLoading] = useState(false);
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

  const toggle = (id: number) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const compute = () => {
    if (selected.size < 2) return;
    setLoading(true);
    setError(false);
    getCorrelations([...selected], timeframe, window)
      .then(setMatrix)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  const cryptoInstruments = instruments.filter((i) => i.asset_class === "crypto");
  const equityInstruments = instruments.filter((i) => i.asset_class === "equity");
  const selectClass =
    "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="mb-3 flex flex-wrap items-end gap-4 text-sm text-[var(--muted)]">
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
              {t("window")}
              <input
                type="number"
                min={2}
                max={200}
                value={window}
                onChange={(e) => setWindowSize(Number(e.target.value))}
                className={`${selectClass} w-20`}
              />
            </label>
            <button
              onClick={compute}
              disabled={selected.size < 2 || loading}
              className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? t("computing") : t("compute")}
            </button>
          </div>
          <p className="mb-3 text-xs text-[var(--muted)]">
            {t("selectionHint", { count: selected.size })}
          </p>

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
                        checked={selected.has(i.id)}
                        onChange={() => toggle(i.id)}
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
                        checked={selected.has(i.id)}
                        onChange={() => toggle(i.id)}
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

        {error && <p className="text-sm text-red-400">{t("error")}</p>}

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("resultsTitle")}
          </h2>
          {!matrix || matrix.pairs.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noResults")}</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-[var(--muted)]">
                    <tr>
                      <th className="py-1 pr-4">{t("columnPair")}</th>
                      <th className="py-1 pr-4">{t("columnPearson")}</th>
                      <th className="py-1 pr-4">{t("columnSpearman")}</th>
                      <th className="py-1 pr-4">{t("columnRolling")}</th>
                      <th className="py-1 pr-4">{t("columnDynamic")}</th>
                      <th className="py-1 pr-4">{t("columnSamples")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.pairs.map((p) => (
                      <tr
                        key={`${p.instrument_a}-${p.instrument_b}`}
                        className="border-t border-white/5"
                      >
                        <td className="py-1.5 pr-4 font-medium">
                          {p.symbol_a} / {p.symbol_b}
                        </td>
                        <td className={`py-1.5 pr-4 ${correlationColor(p.pearson)}`}>
                          {fmt(p.pearson)}
                        </td>
                        <td className={`py-1.5 pr-4 ${correlationColor(p.spearman)}`}>
                          {fmt(p.spearman)}
                        </td>
                        <td className={`py-1.5 pr-4 ${correlationColor(p.rolling)}`}>
                          {fmt(p.rolling)}
                        </td>
                        <td className={`py-1.5 pr-4 ${correlationColor(p.dynamic)}`}>
                          {fmt(p.dynamic)}
                        </td>
                        <td className="py-1.5 pr-4 text-[var(--muted)]">
                          {p.sample_size}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-[var(--muted)]">{matrix.explanation}</p>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
