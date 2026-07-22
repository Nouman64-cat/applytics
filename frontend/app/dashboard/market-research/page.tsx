"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage, ChatSession } from "@/lib/types";
import { btn, btnSecondary, card, errorText, input } from "@/lib/ui";
import Spinner from "@/components/Spinner";

function formatSessionDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={
          isUser
            ? "max-w-[75%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2.5 text-sm text-white shadow-sm"
            : `max-w-[75%] ${card} rounded-bl-sm`
        }
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        {!isUser && message.key_data_points.length > 0 && (
          <ul className="mt-2 space-y-1 border-t border-zinc-100 pt-2 text-xs text-zinc-500">
            {message.key_data_points.map((point, i) => (
              <li key={i} className="flex gap-1.5">
                <span className="text-indigo-400">•</span>
                {point}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function MarketResearchPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  function loadSessions() {
    api.marketResearch
      .listSessions()
      .then(setSessions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load chat history"));
  }

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    setLoadingThread(true);
    api.marketResearch
      .listMessages(activeSessionId)
      .then(setMessages)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load conversation"))
      .finally(() => setLoadingThread(false));
  }, [activeSessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, asking]);

  async function sendQuestion(text: string) {
    const trimmed = text.trim();
    if (!trimmed || asking) return;

    setAsking(true);
    setError(null);
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      {
        id: `pending-${Date.now()}`,
        session_id: activeSessionId ?? "",
        role: "user",
        content: trimmed,
        key_data_points: [],
        suggested_follow_ups: [],
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      const reply = await api.marketResearch.ask(trimmed, activeSessionId);
      setMessages((prev) => [...prev, reply]);
      if (!activeSessionId) {
        setActiveSessionId(reply.session_id);
      }
      loadSessions();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The market research assistant failed to respond");
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("pending-")));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-4">
      <aside className="flex w-64 shrink-0 flex-col gap-2">
        <button
          className={`${btnSecondary} w-full`}
          onClick={() => {
            setActiveSessionId(null);
            setMessages([]);
          }}
        >
          + New chat
        </button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                s.id === activeSessionId
                  ? "bg-indigo-50 text-indigo-700 font-medium"
                  : "text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              <span className="block truncate">{s.title || "New chat"}</span>
              <span className="block text-xs text-zinc-400">{formatSessionDate(s.updated_at)}</span>
            </button>
          ))}
          {sessions.length === 0 && <p className="px-3 py-2 text-xs text-zinc-400">No conversations yet.</p>}
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Market Research</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Ask about trending positions, platform performance, and market shifts — grounded in your scraped jobs
            and application data.
          </p>
        </div>

        <div ref={scrollRef} className="mt-4 flex-1 space-y-3 overflow-y-auto rounded-xl border border-zinc-200/70 bg-zinc-50/50 p-4">
          {loadingThread && (
            <div className="flex items-center gap-2 text-sm text-zinc-500">
              <Spinner className="h-4 w-4" /> Loading conversation…
            </div>
          )}
          {!loadingThread && messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-sm text-zinc-400">
              Ask something like "what positions are trending right now?" or "why is LinkedIn producing fewer leads
              this month?"
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {asking && (
            <div className="flex items-center gap-2 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-700">
              <Spinner className="h-4 w-4" />
              Analyzing market data…
            </div>
          )}
        </div>

        {!asking && messages.length > 0 && messages[messages.length - 1]?.suggested_follow_ups.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {messages[messages.length - 1].suggested_follow_ups.map((chip, i) => (
              <button
                key={i}
                className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
                onClick={() => sendQuestion(chip)}
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {error && <p className={`${errorText} mt-3`}>{error}</p>}

        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            sendQuestion(question);
          }}
        >
          <input
            className={input}
            placeholder="Ask about trends, platforms, or dips…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={asking}
          />
          <button type="submit" className={`${btn} gap-2`} disabled={asking || !question.trim()}>
            {asking && <Spinner />}
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
