"use client";

import { useTranslations } from "next-intl";
import Image from "next/image";
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
        <div className="space-y-3 text-center">
          <Image
            src="/logo-emblem.png"
            alt="IndraQuant"
            width={72}
            height={72}
            priority
            className="mx-auto"
          />
          <h1 className="brand-gradient-text text-3xl font-semibold tracking-tight">
            IndraQuant
          </h1>
          <div className="space-y-1">
            <h2 className="text-xl font-medium">{t("title")}</h2>
            <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
          </div>
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
          className="brand-button w-full rounded-lg px-4 py-2.5 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? t("submitting") : t("submit")}
        </button>
      </form>
    </main>
  );
}
