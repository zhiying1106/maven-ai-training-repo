"use client";

import { SourceBadge, ConfidencePill } from "./SourceBadge";
import type { Message } from "@/lib/types";

// ─── Simple inline markdown renderer ─────────────────────────────────────────

function renderContent(text: string) {
  // Strip the [EXTERNAL] tag that the agent prefixes to external answers
  const cleaned = text.replace(/^\[EXTERNAL\]\s*/i, "");
  const lines = cleaned.split("\n");

  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = (key: string) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={key} className="list-disc pl-5 space-y-0.5">
          {listItems.map((li, i) => (
            <li key={i} className="text-sm text-gray-800">{li}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith("- ") || line.startsWith("• ")) {
      listItems.push(line.slice(2));
    } else {
      flushList(`list-${i}`);
      if (line.trim() === "") {
        elements.push(<div key={`br-${i}`} className="h-1" />);
      } else if (line.startsWith("## ") || line.startsWith("**") && line.endsWith("**")) {
        const txt = line.replace(/^\*\*|\*\*$/g, "").replace(/^##\s*/, "");
        elements.push(
          <p key={i} className="text-sm font-semibold text-gray-900 mt-1">{txt}</p>
        );
      } else {
        elements.push(
          <p key={i} className="text-sm text-gray-800">{line}</p>
        );
      }
    }
  });
  flushList("list-end");

  return <>{elements}</>;
}

// ─── Loading animation ────────────────────────────────────────────────────────

export function LoadingBubble() {
  return (
    <div className="flex items-start gap-2 mb-4">
      <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1">
        R
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 mb-4">
      <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-1">
        R
      </div>
      <div className="min-w-0 flex-1 max-w-[88%]">
        {/* Header: name + confidence pill */}
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="text-xs font-semibold text-gray-600">RepoMind</span>
          {message.confidence && <ConfidencePill confidence={message.confidence} />}
        </div>

        {/* Bubble */}
        <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <div className="space-y-1 leading-relaxed">
            {renderContent(message.content)}
          </div>

          {/* Source citations */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400 font-medium mb-1.5">Sources cited</p>
              <div className="flex flex-wrap gap-1.5">
                {message.sources.map((s) => (
                  <SourceBadge key={s} source={s} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
