"use client";

import { useTranslations } from "next-intl";
import Image from "next/image";

import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { useAuthStore } from "@/lib/stores/auth";

export function AppNav() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();
  const setToken = useAuthStore((state) => state.setToken);

  const linkClass = (href: string) =>
    `rounded-md px-3 py-1.5 text-sm transition-colors ${
      pathname === href
        ? "bg-white/10 text-[var(--foreground)]"
        : "text-[var(--muted)] hover:text-[var(--foreground)]"
    }`;

  const logout = () => {
    setToken(null);
    router.push("/login");
  };

  return (
    <header className="flex flex-wrap items-center justify-between gap-y-2 border-b border-white/10 px-6 py-3">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="flex items-center gap-2">
          <Image
            src="/logo-emblem.png"
            alt=""
            width={28}
            height={28}
            priority
          />
          <span className="brand-gradient-text text-lg font-semibold tracking-tight">
            IndraQuant
          </span>
        </span>
        <nav className="flex flex-wrap items-center gap-1">
          <Link href="/" className={linkClass("/")}>
            {t("dashboard")}
          </Link>
          <Link href="/backtesting" className={linkClass("/backtesting")}>
            {t("backtesting")}
          </Link>
          <Link href="/paper-trading" className={linkClass("/paper-trading")}>
            {t("paperTrading")}
          </Link>
          <Link href="/news" className={linkClass("/news")}>
            {t("news")}
          </Link>
          <Link href="/alerts" className={linkClass("/alerts")}>
            {t("alerts")}
          </Link>
          <Link href="/assistant" className={linkClass("/assistant")}>
            {t("assistant")}
          </Link>
          <Link href="/settings" className={linkClass("/settings")}>
            {t("settings")}
          </Link>
        </nav>
      </div>
      <button
        onClick={logout}
        className="rounded-md px-3 py-1.5 text-sm text-[var(--muted)] transition-colors hover:text-[var(--foreground)]"
      >
        {t("logout")}
      </button>
    </header>
  );
}
