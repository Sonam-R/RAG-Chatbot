const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Source = {
  n: number;
  filename: string;
  page: number;
  snippet: string;
  score: number;
};

export type Document = {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  created_at: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[] | null;
};

export type StreamEvent = {
  conversation_id?: string;
  token?: string;
  error?: string;
  done?: boolean;
  sources?: Source[];
};

async function apiError(res: Response): Promise<Error> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return new Error(detail);
    }
  } catch {
    // response was not JSON
  }
  return new Error(`Request failed (${res.status})`);
}

/**
 * Stream a chat request to the backend. Calls `onEvent` for each SSE data chunk.
 */
export async function streamChat(params: {
  message: string;
  conversationId: string | null;
  useDocuments: boolean;
  signal?: AbortSignal;
  onEvent: (e: StreamEvent) => void;
  onSources?: (sources: Source[]) => void;
}) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message: params.message,
      conversation_id: params.conversationId,
      use_documents: params.useDocuments,
    }),
    signal: params.signal,
  });
  if (!res.ok || !res.body) throw await apiError(res);

  const decoder = new TextDecoder();
  const reader = res.body.getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") {
          params.onEvent({ done: true });
          return;
        }
        try {
          const data = JSON.parse(payload) as StreamEvent & { status?: string };
          if ("status" in data) continue;
          if (Array.isArray(data.sources)) {
            params.onSources?.(data.sources);
            continue;
          }
          if (
            "conversation_id" in data ||
            "token" in data ||
            "error" in data
          ) {
            params.onEvent(data);
          }
        } catch {
          // skip malformed SSE payloads
        }
      }
    }
  }
  params.onEvent({ done: true });
}

export async function fetchConversation(id: string) {
  const res = await fetch(`${API_URL}/api/conversations/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as {
    id: string;
    title: string;
    messages: ChatMessage[];
  };
}

export async function uploadDocument(file: File): Promise<Document> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_URL}/api/documents`, { method: "POST", body });
  if (!res.ok) throw await apiError(res);
  const data = (await res.json()) as {
    doc_id: string;
    filename: string;
    pages: number;
    chunks: number;
  };
  return {
    id: data.doc_id,
    filename: data.filename,
    pages: data.pages,
    chunks: data.chunks,
    created_at: new Date().toISOString(),
  };
}

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_URL}/api/documents`);
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as Document[];
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw await apiError(res);
}
