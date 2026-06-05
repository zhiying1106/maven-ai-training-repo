"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { sendChatMessage, type ChatMessage } from "@/lib/api";

const STARTER_PROMPTS = [
  "I'm feeling stressed about work lately.",
  "Help me build a simple morning routine.",
  "I need a pep talk before a big presentation.",
];

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function submitMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setError(null);
    setInput("");

    const userMessage: ChatMessage = {
      id: createId(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const reply = await sendChatMessage(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: createId(), role: "assistant", content: reply },
      ]);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
      textareaRef.current?.focus();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitMessage(input);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <section
        className="flex min-h-[320px] flex-1 flex-col gap-3 overflow-y-auto rounded-2xl border border-coach-border bg-coach-surface/80 p-4 shadow-inner sm:p-5"
        aria-live="polite"
        aria-label="Conversation"
      >
        {messages.length === 0 && !isLoading ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 py-8 text-center">
            <div className="max-w-md space-y-2">
              <p className="text-lg font-medium text-coach-text">
                What would you like to talk about?
              </p>
              <p className="text-sm text-coach-muted">
                Share what&apos;s on your mind — stress, habits, motivation, or confidence.
                Your coach is here to listen.
              </p>
            </div>
            <div className="flex w-full max-w-lg flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  disabled={isLoading}
                  onClick={() => void submitMessage(prompt)}
                  className="rounded-xl border border-coach-border bg-coach-bg px-4 py-2.5 text-left text-sm text-coach-text transition hover:border-coach-accent hover:bg-coach-bg/80 disabled:opacity-50 sm:text-center"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {messages.map((msg) => (
              <li
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%] sm:text-base ${
                    msg.role === "user"
                      ? "bg-coach-user text-white"
                      : "border border-coach-border bg-coach-bg text-coach-text"
                  }`}
                >
                  <span className="sr-only">
                    {msg.role === "user" ? "You" : "Coach"}:
                  </span>
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>
              </li>
            ))}
            {isLoading && (
              <li className="flex justify-start" aria-busy="true">
                <div className="rounded-2xl border border-coach-border bg-coach-bg px-4 py-3 text-coach-muted">
                  <span className="inline-flex items-center gap-2">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-coach-accent" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-coach-accent [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-pulse rounded-full bg-coach-accent [animation-delay:300ms]" />
                    <span className="sr-only">Coach is typing</span>
                  </span>
                </div>
              </li>
            )}
            <div ref={listEndRef} />
          </ul>
        )}
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/40 bg-red-950/50 px-4 py-3 text-sm text-red-200"
        >
          {error}
          <span className="mt-1 block text-red-300/80">
            Keep the FastAPI server running in its own terminal (port 8000) with{" "}
            <code className="text-red-100">OPENAI_API_KEY</code> set before using the chat.
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor="message" className="sr-only">
          Your message
        </label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <textarea
            ref={textareaRef}
            id="message"
            name="message"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message… (Enter to send, Shift+Enter for new line)"
            disabled={isLoading}
            className="min-h-[52px] flex-1 resize-y rounded-xl border border-coach-border bg-coach-surface px-4 py-3 text-coach-text placeholder:text-coach-muted focus:border-coach-accent focus:outline-none focus:ring-2 focus:ring-coach-accent/30 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="shrink-0 rounded-xl bg-coach-accent px-6 py-3 font-medium text-coach-bg transition hover:bg-coach-accent-hover focus:outline-none focus:ring-2 focus:ring-coach-accent focus:ring-offset-2 focus:ring-offset-coach-bg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? "Sending…" : "Send"}
          </button>
        </div>
        <p className="text-xs text-coach-muted">
          This app is for supportive conversation only — not a substitute for professional care.
        </p>
      </form>
    </div>
  );
}
