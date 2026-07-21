"use client";

import { useTranslations } from "next-intl";
import { FormEvent, useState } from "react";

import { ApiRequestError, login } from "@/lib/api-client/client";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthStore } from "@/lib/stores/auth";

export default function LoginPage() {
  const t = useTranslations("login");
  const router = useRouter();
  const setToken = useAuthStore((state) => state.setToken);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await login(email, password);
      setToken(response.access_token);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiRequestError && err.status === 401
          ? t("invalidCredentials")
          : t("serverError"),
      );
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm outline-none transition-colors focus:border-white/30";

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-5">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <label className="block space-y-1.5">
          <span className="text-sm text-[var(--muted)]">{t("email")}</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm text-[var(--muted)]">{t("password")}</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-white/90 px-4 py-2.5 text-sm font-medium text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? t("submitting") : t("submit")}
        </button>
      </form>
    </main>
  );
}
