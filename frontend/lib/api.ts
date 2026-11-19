const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type StreamEvent = {
  conversation_id?: string;
  token?: string;
  error?: string;
  done?: boolean;
};

export async function streamChat(params: {
  message: string;
  conversationId: string | null;
  signal?: AbortSignal;
  onEvent: (e: StreamEvent) => void;
}) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: params.message,
      conversation_id: params.conversationId,
    }),
    signal: params.signal,
  });
  if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);
