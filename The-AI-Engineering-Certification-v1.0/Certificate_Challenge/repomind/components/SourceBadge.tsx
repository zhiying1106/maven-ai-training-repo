"use client";

import type { Confidence } from "@/lib/types";

const BADGE_CONFIG: Record<
  string,
  { bg: string; text: string; border: string; icon: string }
> = {
  "PR#": { bg: "bg-violet-50", text: "text-violet-800", border: "border-violet-200", icon: "PR" },
  "commit:": { bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", icon: "C" },
  "chat:": { bg: "bg-sky-50", text: "text-sky-800", border: "border-sky-200", icon: "T" },
  "email:": { bg: "bg-rose-50", text: "text-rose-800", border: "border-rose-200", icon: "E" },
  "RFC-": { bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-200", icon: "R" },
  "PROP-": { bg: "bg-teal-50", text: "text-teal-800", border: "border-teal-200", icon: "P" },
  default: { bg: "bg-gray-50", text: "text-gray-700", border: "border-gray-200", icon: "S" },
};

function getBadgeConfig(source: string) {
  for (const [prefix, cfg] of Object.entries(BADGE_CONFIG)) {
    if (source.startsWith(prefix)) return cfg;
  }
  return BADGE_CONFIG.default;
}

export function SourceBadge({ source }: { source: string }) {
  const cfg = getBadgeConfig(source);

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono border ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      <span aria-hidden="true" className="text-[10px] font-semibold">
        {cfg.icon}
      </span>
      {source}
    </span>
  );
}

export function ConfidencePill({ confidence }: { confidence: Confidence }) {
  const config = {
    high: { label: "Grounded", bg: "bg-green-100", text: "text-green-800", icon: "OK" },
    low: { label: "Low confidence", bg: "bg-orange-100", text: "text-orange-800", icon: "!" },
    external: { label: "External knowledge", bg: "bg-blue-100", text: "text-blue-800", icon: "WEB" },
  }[confidence];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
    >
      <span aria-hidden="true" className="text-[10px] font-semibold">
        {config.icon}
      </span>
      {config.label}
    </span>
  );
}
