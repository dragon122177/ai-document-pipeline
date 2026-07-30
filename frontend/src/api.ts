import type {
  AuditEvent,
  Dashboard,
  DocumentDetail,
  DocumentItem,
  ExtractionTemplate,
  Job,
  Review,
  SearchResult,
  Session,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const TOKEN_KEY = "docuflux.session";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message?: string) {
    super(message ?? code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null): void {
  if (session) {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function token(): string | null {
  return loadSession()?.token ?? null;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const authToken = token();
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = `http_${response.status}`;
    let message = response.statusText;
    try {
      const body = await response.json();
      code = body.detail ?? body.error?.code ?? code;
      message = body.error?.message ?? code;
    } catch {
      // Preserve the HTTP fallback when the body is not JSON.
    }
    if (response.status === 401) saveSession(null);
    throw new ApiError(response.status, String(code), String(message));
  }
  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<Session>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  dashboard: () => request<Dashboard>("/dashboard"),
  documents: (params = "") =>
    request<DocumentItem[]>(`/documents${params ? `?${params}` : ""}`),
  document: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  createText: (payload: {
    title: string;
    content: string;
    tags: string[];
    idempotencyKey: string;
  }) =>
    request<{ document: DocumentItem; jobId: string; deduplicated: boolean }>(
      "/documents/text",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  upload: (form: FormData) =>
    request<{ document: DocumentItem; jobId: string; deduplicated: boolean }>(
      "/documents/upload",
      { method: "POST", body: form },
    ),
  process: (id: string) =>
    request<{ jobId: string; status: string }>(`/documents/${id}/process`, {
      method: "POST",
    }),
  jobs: () => request<Job[]>("/jobs"),
  reviews: (status = "PENDING") =>
    request<Review[]>(`/reviews?status=${encodeURIComponent(status)}`),
  decideReview: (
    id: string,
    decision: "APPROVED" | "REJECTED",
    notes: string,
    corrections: Record<string, unknown>,
  ) =>
    request<Review>(`/reviews/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes, corrections }),
    }),
  search: (query: string) =>
    request<SearchResult[]>(`/search?q=${encodeURIComponent(query)}`),
  templates: () => request<ExtractionTemplate[]>("/templates"),
  audit: () => request<AuditEvent[]>("/audit"),
  exportDocument: async (id: string, fileName: string) => {
    const response = await fetch(`${API_BASE}/documents/${id}/export`, {
      headers: token() ? { Authorization: `Bearer ${token()}` } : {},
    });
    if (!response.ok) throw new ApiError(response.status, "export_failed");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
    URL.revokeObjectURL(url);
  },
};

export function streamEvents(
  onEvent: (event: { type: string; data: unknown }) => void,
): () => void {
  const controller = new AbortController();
  const authToken = token();
  if (!authToken) return () => controller.abort();

  void (async () => {
    try {
      const response = await fetch(`${API_BASE}/events`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          Accept: "text/event-stream",
        },
        signal: controller.signal,
      });
      if (!response.ok || !response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!controller.signal.aborted) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const packets = buffer.split("\n\n");
        buffer = packets.pop() ?? "";
        for (const packet of packets) {
          let type = "message";
          let data = "";
          for (const line of packet.split("\n")) {
            if (line.startsWith("event:")) type = line.slice(6).trim();
            if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (data) {
            try {
              onEvent({ type, data: JSON.parse(data) });
            } catch {
              onEvent({ type, data });
            }
          }
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.warn("Realtime connection closed", error);
      }
    }
  })();
  return () => controller.abort();
}
