"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { getSettings, updateSetting } from "@/lib/api-client/client";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [language, setLanguage] = useState("fr");
  const [theme, setTheme] = useState("dark");
  const [maxTokens, setMaxTokens] = useState(512);
  const [temperature, setTemperature] = useState(0.3);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">(
    "idle",
  );
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    getSettings()
      .then(({ settings }) => {
        if (settings.language) setLanguage(settings.language);
        if (settings.theme) setTheme(settings.theme);
        if (settings.ai_max_tokens) setMaxTokens(Number(settings.ai_max_tokens));
        if (settings.ai_temperature) setTemperature(Number(settings.ai_temperature));
      })
      .catch(() => setLoadError(true));
  }, [token]);

  const save = async () => {
    setStatus("saving");
    try {
      await updateSetting("language", language);
      await updateSetting("theme", theme);
      await updateSetting("ai_max_tokens", String(maxTokens));
      await updateSetting("ai_temperature", String(temperature));
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  };

  const selectClass =
    "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-white/30";

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-lg space-y-6 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        {loadError && <p className="text-sm text-red-400">{t("loadError")}</p>}

        <label className="block space-y-1.5">
          <span className="text-sm text-[var(--muted)]">{t("language")}</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className={selectClass}
          >
            <option value="fr">{t("languages.fr")}</option>
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm text-[var(--muted)]">{t("theme")}</span>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className={selectClass}
          >
            <option value="dark">{t("themes.dark")}</option>
            <option value="light">{t("themes.light")}</option>
          </select>
        </label>

        <div className="space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="text-sm font-medium">{t("ai.title")}</h2>

          <label className="block space-y-1.5">
            <span className="text-sm text-[var(--muted)]">{t("ai.maxTokens")}</span>
            <input
              type="number"
              min={64}
              max={32768}
              step={512}
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
              className={selectClass}
            />
            <span className="block text-xs text-[var(--muted)]">
              {t("ai.maxTokensHelp")}
            </span>
          </label>

          <label className="block space-y-1.5">
            <span className="text-sm text-[var(--muted)]">
              {t("ai.temperature")} ({temperature.toFixed(1)})
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              className="w-full accent-white"
            />
            <span className="block text-xs text-[var(--muted)]">
              {t("ai.temperatureHelp")}
            </span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={status === "saving"}
            className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {status === "saving" ? t("saving") : t("save")}
          </button>
          {status === "saved" && (
            <span className="text-sm text-emerald-400">{t("saved")}</span>
          )}
          {status === "error" && (
            <span className="text-sm text-red-400">{t("saveError")}</span>
          )}
        </div>
      </main>
    </div>
  );
}
