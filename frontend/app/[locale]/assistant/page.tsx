"use client";

import { useTranslations } from "next-intl";
import { FormEvent, useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { chatWithAssistant } from "@/lib/api-client/client";
import type { ChatMessage } from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

export default function AssistantPage() {
  const t = useTranslations("assistant");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);
  const [contextNote, setContextNote] = useState<string | null>(null);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || sending) return;

    const history = messages;
    const userMessage: ChatMessage = { role: "user", content: input.trim() };
    setMessages([...history, userMessage]);
    setInput("");
    setSending(true);
    setError(false);

    chatWithAssistant(userMessage.content, history)
      .then((response) => {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: response.reply },
        ]);
        setContextNote(response.context_note);
      })
      .catch(() => setError(true))
      .finally(() => setSending(false));
  };

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-8">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-sm text-[var(--muted)]">{t("subtitle")}</p>
        </div>

        <div className="min-h-[400px] space-y-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          {messages.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">{t("empty")}</p>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={
                  message.role === "user"
                    ? "ml-auto max-w-[80%] rounded-xl bg-white/10 px-4 py-2 text-sm"
                    : "mr-auto max-w-[80%] rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm"
                }
              >
                {message.content}
              </div>
            ))
          )}
          {sending && (
            <p className="text-sm text-[var(--muted)]">{t("sending")}</p>
          )}
        </div>

        {error && <p className="text-sm text-red-400">{t("error")}</p>}

        <form onSubmit={submit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("placeholder")}
            className="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm outline-none focus:border-white/30"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="brand-button rounded-lg px-4 py-2.5 text-sm font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {t("send")}
          </button>
        </form>

        <p className="text-xs text-[var(--muted)]">
          {contextNote ?? t("disclaimer")}
        </p>
      </main>
    </div>
  );
}
