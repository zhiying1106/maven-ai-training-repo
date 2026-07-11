// ─── Query classification ────────────────────────────────────────────────────

export type QueryType = "why" | "what-breaks" | "external" | "general";

export type Confidence = "high" | "low" | "external";

// ─── Chat types ───────────────────────────────────────────────────────────────

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  confidence?: Confidence;
  queryType?: QueryType;
  timestamp: number;
}

// ─── API types ────────────────────────────────────────────────────────────────

export interface AgentResponse {
  answer: string;
  sources: string[];
  confidence: Confidence;
  queryType: QueryType;
}
