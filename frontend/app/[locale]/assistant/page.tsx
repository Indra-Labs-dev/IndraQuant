"use client";

import { useTranslations } from "next-intl";
import { FormEvent, useEffect, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { AppNav } from "@/components/layout/AppNav";
import {
  chatWithAssistant,
  clearAssistantMemory,
  getAssistantMemory,
  getChatHistory,
} from "@/lib/api-client/client";
import type { ChatMessage } from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

// Compact overrides so markdown (lists, code, links...) reads well inside a
// narrow chat bubble instead of using react-markdown's default block spacing.
const markdownComponents: Components = {
  p: ({ children }) => <p className="whitespace-pre-wrap [&:not(:first-child)]:mt-2">{children}</p>,
  ul: ({ children }) => <ul className="ml-4 list-outside list-disc space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="ml-4 list-outside list-decimal space-y-0.5">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline decoration-dotted hover:text-white"
    >
      {children}
    </a>
  ),
  code: ({ children, className }) => {
    const isBlock = className?.includes("language-");
    return isBlock ? (
      <code className={className}>{children}</code>
    ) : (
      <code className="rounded bg-black/30 px-1 py-0.5 text-[0.85em]">{children}</code>
    );
  },
  pre: ({ children }) => (
    <pre className="mt-2 overflow-x-auto rounded-lg bg-black/30 p-2 text-xs">{children}</pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mt-2 border-l-2 border-white/20 pl-3 text-[var(--muted)]">
      {children}
    </blockquote>
  ),
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  h1: ({ children }) => <p className="mt-2 font-semibold">{children}</p>,
  h2: ({ children }) => <p className="mt-2 font-semibold">{children}</p>,
  h3: ({ children }) => <p className="mt-2 font-semibold">{children}</p>,
};

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {content}
    </ReactMarkdown>
  );
}

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
  const [memoryFacts, setMemoryFacts] = useState<string[]>([]);
  const [clearingMemory, setClearingMemory] = useState(false);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!hydrated || !token) return;
    getChatHistory()
      .then((response) => setMessages(response.messages))
      .catch(() => undefined);
    getAssistantMemory()
      .then((response) => setMemoryFacts(response.facts))
      .catch(() => undefined);
  }, [hydrated, token]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || sending) return;

    const userMessage: ChatMessage = { role: "user", content: input.trim() };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    setError(false);

    chatWithAssistant(userMessage.content)
      .then((response) => {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: response.reply },
        ]);
        setContextNote(response.context_note);
        return getAssistantMemory();
      })
      .then((response) => setMemoryFacts(response.facts))
      .catch(() => setError(true))
      .finally(() => setSending(false));
  };

  const clearMemory = () => {
    if (clearingMemory) return;
    setClearingMemory(true);
    clearAssistantMemory()
      .then((response) => setMemoryFacts(response.facts))
      .catch(() => undefined)
      .finally(() => setClearingMemory(false));
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
                <MarkdownMessage content={message.content} />
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

        <div className="space-y-2 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">{t("memory.title")}</h2>
            {memoryFacts.length > 0 && (
              <button
                type="button"
                onClick={clearMemory}
                disabled={clearingMemory}
                className="text-xs text-[var(--muted)] underline decoration-dotted hover:text-white disabled:opacity-50"
              >
                {t("memory.clear")}
              </button>
            )}
          </div>
          {memoryFacts.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">{t("memory.empty")}</p>
          ) : (
            <ul className="list-inside list-disc space-y-1 text-xs text-[var(--muted)]">
              {memoryFacts.map((fact, index) => (
                <li key={index}>{fact}</li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
