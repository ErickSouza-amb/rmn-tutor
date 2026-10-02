import { describe, expect, it } from "vitest";
import { createSSEParser } from "./sse";

describe("createSSEParser", () => {
  it("parses frames split across chunks", () => {
    const got: { event: string; data: string }[] = [];
    const p = createSSEParser((m) => got.push(m));
    p.push("event: text_delta\nda");
    p.push('ta: {"text":"Ol');
    p.push('á"}\n\nevent: done\ndata: {}\n\n');
    expect(got).toEqual([
      { event: "text_delta", data: '{"text":"Olá"}' },
      { event: "done", data: "{}" },
    ]);
  });

  it("handles CRLF split between chunks, comments and multi-line data", () => {
    const got: { event: string; data: string }[] = [];
    const p = createSSEParser((m) => got.push(m));
    p.push(": ping\r\n\r\nevent: x\r");
    p.push("\ndata: a\r\ndata: b\r\n\r\n");
    expect(got).toEqual([{ event: "x", data: "a\nb" }]);
  });

  it("defaults event name to message", () => {
    const got: { event: string; data: string }[] = [];
    createSSEParser((m) => got.push(m)).push("data: 1\n\n");
    expect(got).toEqual([{ event: "message", data: "1" }]);
  });
});
