const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type StreamEvent = {
  conversation_id?: string;
  token?: string;
  error?: string;
  done?: boolean;
};

/**
 * Stream a chat request to the backend. Calls `onEvent` for each SSE data chunk.
 */
export async function streamChat(params: {
  message: string;
  conversationId: string | null;
  signal?: AbortSignal;
  onEvent: (e: StreamEvent) => void;
}) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify({
      message: params.message,
      conversation_id: params.conversationId,
    }),
    signal: params.signal,
  });
  if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);

  // Parse Server‑Sent Events stream
  const decoder = new TextDecoder();
  const reader = res.body.getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // keep incomplete line
    for (const raw of lines) {
      console.log('raw line from SSE:', raw);
      const line = raw.trim();
      if (!line) continue;
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") {
          params.onEvent({ done: true });
          return;
        }
        try {
          const data: StreamEvent = JSON.parse(payload);
          params.onEvent(data);
        } catch (e) {
          // ignore malformed line
        }
      }
    }
  }
  // End of stream without explicit [DONE]
  params.onEvent({ done: true });
}

/**
 * Fetch a conversation by ID. Returns null if the conversation does not exist.
 */
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
