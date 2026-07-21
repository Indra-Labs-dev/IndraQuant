"use client";

import { useTranslations } from "next-intl";

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
    <header className="flex items-center justify-between border-b border-white/10 px-6 py-3">
      <div className="flex items-center gap-6">
        <span className="text-lg font-semibold tracking-tight">IndraQuant</span>
        <nav className="flex items-center gap-1">
          <Link href="/" className={linkClass("/")}>
            {t("dashboard")}
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
