import { readSSE } from "./sse";
import type {
  AssistMode,
  ExercisePublic,
  ParseResult,
  Peak,
  SessionData,
  SessionMetadata,
  SessionSummary,
  Spectrum,
  StructureCheck,
  TurnEvent,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "http_error";
  let message = `Erro ${res.status}`;
  try {
    const body = await res.json();
    code = body?.error?.code ?? code;
    message = body?.error?.message ?? message;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, { credentials: "same-origin", ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } });
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

export function imageUrl(id: string): string {
  return `/api/sessions/${id}/image`;
}

export const api = {
  health: () => request<{ status: string; db: string; tutor: "simulated" | "claude" }>("/health"),
  listExercises: () => request<ExercisePublic[]>("/exercises"),
  listSessions: () => request<SessionSummary[]>("/sessions"),
  createSession: (body: { exercise_id?: string; metadata?: SessionMetadata; peaks?: Peak[]; title?: string }) =>
    request<{ id: string }>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  getSession: (id: string) => request<SessionData>(`/sessions/${id}`),
  updateSession: (id: string, body: { metadata?: SessionMetadata; peaks?: Peak[]; assist_mode?: AssistMode; title?: string }) =>
    request<SessionData>(`/sessions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  uploadImage: (id: string, file: Blob, filename: string) => {
    const form = new FormData();
    form.append("file", file, filename);
    return request<{ ok: boolean; media_type: string }>(`/sessions/${id}/image`, { method: "POST", body: form });
  },
  parsePeaks: (text: string) => request<ParseResult>("/peaks/parse", { method: "POST", body: JSON.stringify({ text }) }),
  getSpectrum: (id: string) => request<Spectrum>(`/sessions/${id}/spectrum`),
  structureCheck: (id: string, smiles: string) =>
    request<StructureCheck>(`/sessions/${id}/structure-check`, { method: "POST", body: JSON.stringify({ smiles }) }),
  async sendMessage(id: string, text: string, mode: AssistMode | null, onEvent: (e: TurnEvent) => void): Promise<void> {
    const res = await fetch(`/api/sessions/${id}/messages`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(mode ? { text, mode } : { text }),
    });
    if (!res.ok) throw await toApiError(res);
    const type = res.headers.get("content-type") ?? "";
    if (type.includes("application/json")) {
      const body = (await res.json()) as { events: TurnEvent[] };
      body.events.forEach(onEvent);
      return;
    }
    if (!res.body) throw new ApiError(500, "no_stream", "Resposta sem corpo.");
    await readSSE(res.body, (m) => onEvent({ event: m.event, data: JSON.parse(m.data) } as TurnEvent));
  },
};
