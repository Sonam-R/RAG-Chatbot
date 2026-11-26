import { MAX_UPLOAD_MB } from "./constants";

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

export type VerificationResult = {
  status: "ok" | "unverified";
  invalid_citations?: number[];
  missing_citation?: boolean;
  unsupported_numbers?: number[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[] | null;
  statusText?: string | null;
  verification?: VerificationResult | null;
  isRefusal?: boolean;
};

export type StreamEvent = {
  conversation_id?: string;
  token?: string;
  error?: string;
  done?: boolean;
  sources?: Source[];
  status?: string;
  verification?: VerificationResult;
};

async function apiError(res: Response): Promise<Error> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object") {
      if ("error" in body && typeof (body as { error: unknown }).error === "string") {
        return new Error((body as { error: string }).error);
      }
      if ("detail" in body) {
        const detail = (body as { detail: unknown }).detail;
        if (typeof detail === "string") return new Error(detail);
        if (detail && typeof detail === "object" && "error" in detail) {
          const msg = (detail as { error: unknown }).error;
          if (typeof msg === "string") return new Error(msg);
        }
      }
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

  const dispatchPayload = (payload: string) => {
    if (payload === "[DONE]") {
      params.onEvent({ done: true });
      return true;
    }
    try {
      const data = JSON.parse(payload) as StreamEvent & {
        status?: string;
        verification?: VerificationResult;
        sources?: Source[];
      };
      if (typeof data.status === "string") {
        params.onEvent({ status: data.status });
      }
      if (data.verification) {
        params.onEvent({ verification: data.verification });
      }
      if (Array.isArray(data.sources)) {
        params.onSources?.(data.sources);
      }
      if (
        typeof data.conversation_id === "string" ||
        typeof data.token === "string" ||
        typeof data.error === "string"
      ) {
        params.onEvent(data);
      }
    } catch {
      // skip malformed SSE payloads
    }
    return false;
  };

  const decoder = new TextDecoder();
  const reader = res.body.getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, "\n");
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      for (const raw of block.split("\n")) {
        const line = raw.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (dispatchPayload(payload)) return;
      }
    }
  }
  if (buffer.trim()) {
    for (const raw of buffer.split("\n")) {
      const line = raw.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (dispatchPayload(payload)) return;
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

export function mapUploadHttpError(status: number): string {
  if (status === 400) return "Unsupported file type. Use PDF, TXT, or MD.";
  if (status === 413) return `File is too large (max ${MAX_UPLOAD_MB} MB).`;
  if (status === 422)
    return "No readable text in this file. Scanned PDFs are not supported yet.";
  if (status === 0) return "Network error. Check your connection.";
  return `Upload failed (${status}).`;
}

export async function uploadDocument(file: File): Promise<Document> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${API_URL}/api/documents`, { method: "POST", body });
  if (!res.ok) throw new Error(mapUploadHttpError(res.status));
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

/** XMLHttpRequest upload for progress / clear processing phases. */
export function uploadDocumentXHR(
  file: File,
  onProgress?: (loaded: number, total: number) => void,
): Promise<Document> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const body = new FormData();
    body.append("file", file);
    xhr.open("POST", `${API_URL}/api/documents`);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as {
            doc_id: string;
            filename: string;
            pages: number;
            chunks: number;
          };
          resolve({
            id: data.doc_id,
            filename: data.filename,
            pages: data.pages,
            chunks: data.chunks,
            created_at: new Date().toISOString(),
          });
        } catch {
          reject(new Error("Invalid server response"));
        }
        return;
      }
      reject(new Error(mapUploadHttpError(xhr.status)));
    };
    xhr.onerror = () => reject(new Error(mapUploadHttpError(0)));
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(e.loaded, e.total);
    };
    xhr.send(body);
  });
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
