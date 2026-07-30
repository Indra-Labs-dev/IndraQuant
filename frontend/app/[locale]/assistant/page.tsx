"use client";

import { useTranslations } from "next-intl";
import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { AppNav } from "@/components/layout/AppNav";
import {
  chatWithAssistant,
  clearAssistantMemory,
  getAssistantMemory,
  getConversationHistory,
  listConversations,
} from "@/lib/api-client/client";
import type { ChatMessage, ConversationSummary } from "@/lib/api-client/types";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const AVATAR_GRADIENT = {
  background:
    "linear-gradient(135deg, var(--accent-cyan), var(--accent), var(--accent-violet))",
};

const MAX_TEXTAREA_HEIGHT = 200;

// Compact overrides so markdown (lists, code, links...) reads well at
// conversation width instead of using react-markdown's default block spacing.
const markdownComponents: Components = {
  p: ({ children }) => <p className="whitespace-pre-wrap [&:not(:first-child)]:mt-3">{children}</p>,
  ul: ({ children }) => <ul className="ml-4 list-outside list-disc space-y-1 [&:not(:first-child)]:mt-3">{children}</ul>,
  ol: ({ children }) => <ol className="ml-4 list-outside list-decimal space-y-1 [&:not(:first-child)]:mt-3">{children}</ol>,
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
    <pre className="mt-3 overflow-x-auto rounded-lg bg-black/30 p-3 text-xs">{children}</pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mt-3 border-l-2 border-white/20 pl-3 text-[var(--muted)]">
      {children}
    </blockquote>
  ),
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  h1: ({ children }) => <p className="mt-3 font-semibold">{children}</p>,
  h2: ({ children }) => <p className="mt-3 font-semibold">{children}</p>,
  h3: ({ children }) => <p className="mt-3 font-semibold">{children}</p>,
};

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {content}
    </ReactMarkdown>
  );
}

function AssistantAvatar() {
  return (
    <div
      style={AVATAR_GRADIENT}
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-white"
    >
      IA
    </div>
  );
}

export default function AssistantPage() {
  const t = useTranslations("assistant");
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);
  const [contextNote, setContextNote] = useState<string | null>(null);
  const [toolsInvoked, setToolsInvoked] = useState<string[]>([]);
  const [memoryFacts, setMemoryFacts] = useState<string[]>([]);
  const [clearingMemory, setClearingMemory] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);

  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  useEffect(() => {
    if (!hydrated || !token) return;
    listConversations()
      .then((response) => {
        setConversations(response.conversations);
        const mostRecent = response.conversations[0];
        if (mostRecent) {
          setActiveConversationId(mostRecent.id);
          return getConversationHistory(mostRecent.id).then((history) =>
            setMessages(history.messages),
          );
        }
      })
      .catch(() => undefined);
    getAssistantMemory()
      .then((response) => setMemoryFacts(response.facts))
      .catch(() => undefined);
  }, [hydrated, token]);

  const openConversation = (conversationId: number) => {
    if (conversationId === activeConversationId) return;
    setActiveConversationId(conversationId);
    setMessages([]);
    setContextNote(null);
    setToolsInvoked([]);
    getConversationHistory(conversationId)
      .then((history) => setMessages(history.messages))
      .catch(() => undefined);
  };

  const startNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setContextNote(null);
    setToolsInvoked([]);
    setInput("");
    textareaRef.current?.focus();
  };

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || sending) return;

    const userMessage: ChatMessage = { role: "user", content: input.trim() };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    setError(false);
    setToolsInvoked([]);
    requestAnimationFrame(() => {
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    });

    chatWithAssistant(userMessage.content, activeConversationId)
      .then((response) => {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: response.reply },
        ]);
        setContextNote(response.context_note);
        setToolsInvoked(response.tools_invoked);
        setActiveConversationId(response.conversation_id);
        listConversations()
          .then((list) => setConversations(list.conversations))
          .catch(() => undefined);
        return getAssistantMemory();
      })
      .then((response) => setMemoryFacts(response.facts))
      .catch(() => setError(true))
      .finally(() => setSending(false));
  };

  const onTextareaKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit(event as unknown as FormEvent);
    }
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
    <div className="flex h-screen flex-col overflow-hidden">
      <AppNav />

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-64 shrink-0 flex-col border-r border-white/10 overflow-hidden">
          <div className="p-3">
            <button
              type="button"
              onClick={startNewConversation}
              className="flex w-full items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm transition-colors hover:bg-white/5"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
              </svg>
              {t("newConversation")}
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
            <p className="px-2 pb-1 text-xs font-medium text-[var(--muted)]">
              {t("conversations.title")}
            </p>
            {conversations.length === 0 ? (
              <p className="px-2 py-2 text-xs text-[var(--muted)]">
                {t("conversations.empty")}
              </p>
            ) : (
              <ul className="space-y-0.5">
                {conversations.map((conversation) => (
                  <li key={conversation.id}>
                    <button
                      type="button"
                      onClick={() => openConversation(conversation.id)}
                      className={`w-full truncate rounded-lg px-2 py-2 text-left text-sm transition-colors ${
                        conversation.id === activeConversationId
                          ? "bg-white/10 text-[var(--foreground)]"
                          : "text-[var(--muted)] hover:bg-white/5 hover:text-[var(--foreground)]"
                      }`}
                    >
                      {conversation.title || t("conversations.untitled")}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">{t("title")}</h1>
            <p className="text-xs text-[var(--muted)]">{t("subtitle")}</p>
          </div>
          <button
            type="button"
            onClick={() => setMemoryOpen((open) => !open)}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-[var(--muted)] transition-colors hover:text-[var(--foreground)]"
          >
            {t("memory.title")}
            {memoryFacts.length > 0 && ` (${memoryFacts.length})`}
          </button>
        </div>

        {memoryOpen && (
          <div className="border-b border-white/10 bg-white/[0.02] px-6 py-4">
            <div className="mx-auto max-w-3xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--muted)]">
                  {t("memory.title")}
                </span>
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
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto px-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-6 py-6">
            {messages.length === 0 ? (
              <p className="py-16 text-center text-sm text-[var(--muted)]">
                {t("empty")}
              </p>
            ) : (
              messages.map((message, index) =>
                message.role === "user" ? (
                  <div key={index} className="flex justify-end">
                    <div className="max-w-[75%] rounded-2xl bg-white/10 px-4 py-2.5 text-sm">
                      {message.content}
                    </div>
                  </div>
                ) : (
                  <div key={index} className="flex gap-3">
                    <AssistantAvatar />
                    <div className="min-w-0 flex-1 pt-0.5 text-sm leading-relaxed">
                      <MarkdownMessage content={message.content} />
                    </div>
                  </div>
                ),
              )
            )}
            {sending && (
              <div className="flex gap-3">
                <AssistantAvatar />
                <div className="flex items-center gap-1 pt-2.5">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted)] [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted)] [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--muted)]" />
                </div>
              </div>
            )}
            <div ref={scrollAnchorRef} />
          </div>
        </div>

        <div className="border-t border-white/10 px-6 py-4">
          <div className="mx-auto max-w-3xl space-y-2">
            {error && <p className="text-sm text-red-400">{t("error")}</p>}

            <form
              onSubmit={submit}
              className="flex items-end gap-2 rounded-2xl border border-white/10 bg-white/5 p-2 focus-within:border-white/30"
            >
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  resizeTextarea();
                }}
                onKeyDown={onTextareaKeyDown}
                placeholder={t("placeholder")}
                className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                aria-label={t("send")}
                className="brand-button flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-opacity hover:opacity-90 disabled:opacity-40"
              >
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" />
                </svg>
              </button>
            </form>

            <p className="text-center text-xs text-[var(--muted)]">
              {contextNote ?? t("disclaimer")}
            </p>
            {toolsInvoked.length > 0 && (
              <p className="text-center text-xs text-[var(--muted)]">
                {t("toolsInvoked", { tools: toolsInvoked.join(", ") })}
              </p>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
