export function getMessageText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === "string") return block;
        if (block && typeof block === "object" && "text" in block) {
          return String((block as { text?: unknown }).text ?? "");
        }
        return "";
      })
      .join("");
  }
  return "";
}

export function shouldDisplayMessage(message: {
  type?: string;
  content?: unknown;
}): boolean {
  if (message.type === "human" || message.type === "tool") {
    return true;
  }

  const text = getMessageText(message.content).trim();
  if (!text) {
    return false;
  }

  const normalized = text.replace(/[^a-z0-9]/gi, "").toUpperCase();
  return normalized !== "APPROVE" && normalized !== "RETRY";
}

export function toolLabel(name?: string): string {
  switch (name) {
    case "retrieve_information":
      return "Knowledge base";
    case "tavily_search":
    case "tavily_search_results_json":
      return "Web search";
    case "arxiv":
      return "Arxiv";
    default:
      return name ?? "tool";
  }
}
