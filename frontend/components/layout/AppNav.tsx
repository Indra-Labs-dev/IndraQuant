"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import Image from "next/image";

import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { useAuthStore } from "@/lib/stores/auth";

const NAV_ITEMS = [
  { href: "/", key: "dashboard" },
  { href: "/backtesting", key: "backtesting" },
  { href: "/paper-trading", key: "paperTrading" },
  { href: "/portfolio", key: "portfolio" },
  { href: "/training", key: "training" },
  { href: "/news", key: "news" },
  { href: "/alerts", key: "alerts" },
  { href: "/assistant", key: "assistant" },
  { href: "/settings", key: "settings" },
] as const;

export function AppNav() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();
  const setToken = useAuthStore((state) => state.setToken);

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
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "text-[var(--foreground)]"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="nav-active-pill"
                    className="absolute inset-0 -z-10 rounded-md bg-white/10"
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
                {t(item.key)}
              </Link>
            );
          })}
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
