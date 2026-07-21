import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("home");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">{t("title")}</h1>
      <p className="max-w-md text-[var(--muted)]">{t("tagline")}</p>
      <p className="rounded-full border border-white/10 px-4 py-1 text-sm text-[var(--muted)]">
        <span className="font-medium text-[var(--foreground)]">
          {t("phaseLabel")}
        </span>{" "}
        — {t("phaseStatus")}
      </p>
    </main>
  );
}
