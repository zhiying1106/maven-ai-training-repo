"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LoadingBubble, MessageBubble } from "./MessageBubble";
import type { AgentResponse, Message } from "@/lib/types";

const SAMPLE_QUESTIONS = [
  "Why did we switch the payment service from an in-memory cache to Redis?",
  "What breaks if I change the calculate_discount() function?",
  "Who decided we'd use PostgreSQL instead of MongoDB for the orders table, and why?",
  "Is there a reason the retry logic in api_client.py uses exponential backoff?",
  "What was the outcome of the RFC about splitting the monolith into microservices?",
  "Summarize what changed in the auth module in the last few months and why",
  "Has anyone raised concerns about the current rate-limiting approach?",
  "What was the original business case for splitting the monolith?",
  "What's the current best practice for rate limiting in FastAPI?",
];

function EmptyState({ onSelect }: { onSelect: (q: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600 text-3xl font-bold text-white shadow-lg">
        R
      </div>
      <h2 className="mb-2 text-2xl font-bold text-gray-900">Ask RepoMind anything</h2>
      <p className="mb-8 max-w-md text-sm leading-relaxed text-gray-500">
        I know the why behind commits, PRs, tickets, docs, chat, and email in the Northwind
        Analytics demo corpus.
      </p>
      <div className="grid w-full max-w-lg grid-cols-1 gap-2">
        {SAMPLE_QUESTIONS.slice(0, 5).map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="rounded-lg border border-indigo-200 px-4 py-2.5 text-left text-sm text-indigo-700 transition-colors hover:bg-indigo-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [input]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);
      setError(null);

      try {
        const history = messages.slice(-10).map((message) => ({
          role: message.role,
          content: message.content,
        }));

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: trimmed, history }),
        });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error ?? "Request failed");
        }

        const data: AgentResponse = await res.json();

        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: data.answer,
            sources: data.sources,
            confidence: data.confidence,
            queryType: data.queryType,
            timestamp: Date.now(),
          },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      } finally {
        setIsLoading(false);
        textareaRef.current?.focus();
      }
    },
    [messages, isLoading]
  );

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <aside className="hidden w-64 flex-shrink-0 flex-col border-r border-gray-200 bg-white p-5 md:flex">
        <div className="mb-1 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-base font-bold text-white shadow">
            R
          </div>
          <div>
            <h1 className="font-bold leading-none text-gray-900">RepoMind</h1>
            <p className="text-xs text-gray-400">Engineering knowledge agent</p>
          </div>
        </div>

        <hr className="my-4 border-gray-100" />

        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          Try asking
        </p>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {SAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => sendMessage(q)}
              disabled={isLoading}
              className="w-full rounded-lg px-2.5 py-1.5 text-left text-xs leading-snug text-gray-600 transition-colors hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-40"
            >
              {q.length > 58 ? `${q.slice(0, 58)}...` : q}
            </button>
          ))}
        </div>

        <div className="mt-4 space-y-1 border-t border-gray-100 pt-4 text-[10px] text-gray-400">
          <p className="flex items-center gap-1.5">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-400" />
            Northwind Analytics synthetic data
          </p>
          <p>Commits / PRs / Tickets / Docs / Chat / Email</p>
          <p className="mt-1 text-gray-300">Powered by OpenAI</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-shrink-0 items-center gap-2 border-b border-gray-200 bg-white px-4 py-3 shadow-sm md:hidden">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-indigo-600 text-xs font-bold text-white">
            R
          </div>
          <h1 className="text-sm font-bold text-gray-900">RepoMind</h1>
          <span className="truncate text-xs text-gray-400">Engineering knowledge agent</span>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 && !isLoading ? (
            <EmptyState onSelect={sendMessage} />
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isLoading && <LoadingBubble />}
              {error && (
                <div className="my-3 flex justify-center">
                  <div className="max-w-sm rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-center text-xs text-red-700">
                    {error}
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </main>

        <footer className="flex-shrink-0 border-t border-gray-200 bg-white px-4 py-3">
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about any code decision, architectural choice, or change history..."
              rows={1}
              disabled={isLoading}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm leading-relaxed focus:border-transparent focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50"
              style={{ minHeight: "42px", maxHeight: "120px" }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={isLoading || !input.trim()}
              aria-label="Send"
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:bg-gray-300"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M3.105 2.289a.75.75 0 0 0-.826.95l1.414 4.925A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.896 28.896 0 0 0 15.293-7.154.75.75 0 0 0 0-1.115A28.897 28.897 0 0 0 3.105 2.289z" />
              </svg>
            </button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-gray-400">
            Enter to send / Shift+Enter for a new line
          </p>
        </footer>
      </div>
    </div>
  );
}
