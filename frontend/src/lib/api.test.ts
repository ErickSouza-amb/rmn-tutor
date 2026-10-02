import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";
import type { TurnEvent } from "./types";

function streamOf(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(c) {
      c.enqueue(bytes.slice(0, 10));
      c.enqueue(bytes.slice(10));
      c.close();
    },
  });
}

afterEach(() => vi.restoreAllMocks());

describe("api", () => {
  it("throws ApiError with backend code", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "session_not_found", message: "Sessão não encontrada." } }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(api.getSession("x")).rejects.toMatchObject({ status: 404, code: "session_not_found" });
    await expect(api.getSession("x")).rejects.toBeInstanceOf(ApiError);
  });

  it("sendMessage dispatches SSE events in order", async () => {
    const body =
      'event: text_delta\ndata: {"text":"Oi"}\n\n' +
      'event: tool_call\ndata: {"name":"get_peak_list","input":{}}\n\n' +
      'event: done\ndata: {"text":"Oi","chem_state":{},"assist_mode":"tutor"}\n\n';
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(streamOf(body), { status: 200, headers: { "content-type": "text/event-stream" } }),
    );
    const events: TurnEvent[] = [];
    await api.sendMessage("s1", "Oi", "tutor", (e) => events.push(e));
    expect(events.map((e) => e.event)).toEqual(["text_delta", "tool_call", "done"]);
  });

  it("sendMessage surfaces JSON errors before streaming", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "turn_in_progress", message: "O tutor ainda está respondendo." } }), {
        status: 409,
        headers: { "content-type": "application/json" },
      }),
    );
    await expect(api.sendMessage("s1", "Oi", null, () => {})).rejects.toMatchObject({ code: "turn_in_progress" });
  });
});
