"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import {
  getCalendarEvents,
  getNews,
  getNewsSentiment,
} from "@/lib/api-client/client";
import type {
  CalendarResponse,
  NewsItem,
  SentimentResponse,
} from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

function sentimentColor(sentiment: string): string {
  if (sentiment === "positif") return "text-[var(--up)]";
  if (sentiment === "negatif") return "text-[var(--down)]";
  return "text-[var(--muted)]";
}

export default function NewsPage() {
  const t = useTranslations("news");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [news, setNews] = useState<NewsItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentResponse | null>(null);
  const [calendar, setCalendar] = useState<CalendarResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [sentimentError, setSentimentError] = useState(false);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!token) return;
    getNews(20)
      .then((r) => setNews(r.items))
      .catch(() => {});
    getCalendarEvents().then(setCalendar).catch(() => {});
  }, [token]);

  const analyze = () => {
    setAnalyzing(true);
    setSentimentError(false);
    getNewsSentiment(8)
      .then(setSentiment)
      .catch(() => setSentimentError(true))
      .finally(() => setAnalyzing(false));
  };

  if (!hydrated || !token) return null;

  const sentimentByTitle = new Map(
    sentiment?.items.map((i) => [i.title, i]) ?? [],
  );

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={analyze}
            disabled={analyzing}
            className="brand-button rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {analyzing ? t("analyzing") : t("analyze")}
          </button>
          {sentiment && (
            <span className="text-sm text-[var(--muted)]">
              {t("averageScore")} :{" "}
              <strong
                className={
                  sentiment.average_score > 0.15
                    ? "text-[var(--up)]"
                    : sentiment.average_score < -0.15
                      ? "text-[var(--down)]"
                      : "text-[var(--foreground)]"
                }
              >
                {sentiment.average_score >= 0 ? "+" : ""}
                {sentiment.average_score.toFixed(2)}
              </strong>
            </span>
          )}
        </div>
        {sentimentError && (
          <p className="text-sm text-red-400">{t("sentimentError")}</p>
        )}
        {sentiment && (
          <p className="text-xs text-[var(--muted)]">{sentiment.explanation}</p>
        )}

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("headlines")}
          </h2>
          {news.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noNews")}</p>
          ) : (
            <ul className="space-y-3">
              {news.map((item, index) => {
                const s = sentimentByTitle.get(item.title);
                return (
                  <li key={`${item.link}-${index}`} className="space-y-0.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
                      {s && (
                        <span
                          className={`text-xs font-medium ${sentimentColor(s.sentiment)}`}
                        >
                          [{t(`sentiments.${s.sentiment}`)} {s.score >= 0 ? "+" : ""}
                          {s.score.toFixed(2)}]
                        </span>
                      )}
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:underline"
                      >
                        {item.title}
                      </a>
                    </div>
                    <p className="text-xs text-[var(--muted)]">
                      {item.source}
                      {item.published_at
                        ? ` — ${new Date(item.published_at).toLocaleString("fr-FR")}`
                        : ""}
                      {s?.rationale ? ` — ${s.rationale}` : ""}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--muted)]">
            {t("calendar")}
          </h2>
          {!calendar || calendar.events.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("noEvents")}</p>
          ) : (
            <>
              <ul className="space-y-1.5">
                {calendar.events.map((event, index) => (
                  <li
                    key={`${event.date}-${index}`}
                    className="flex flex-wrap items-baseline gap-x-3 text-sm"
                  >
                    <span className="font-medium">
                      {new Date(event.date).toLocaleDateString("fr-FR")}
                    </span>
                    <span>{event.name}</span>
                    <span className="text-xs text-[var(--accent-orange)]">
                      {t(`importance.${event.importance}`)}
                    </span>
                    <span className="w-full text-xs text-[var(--muted)]">
                      {event.note}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-[var(--muted)]">
                {calendar.source_note}
              </p>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
