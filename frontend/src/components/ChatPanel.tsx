"use client";

import { api, ApiError } from "@/lib/api";
import { toolLabel } from "@/lib/tools";
import type { AssistMode, ChatMessage, ChemState, SessionData } from "@/lib/types";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ModeSelector } from "./ModeSelector";

interface Draft {
  text: string;
  tools: string[];
}

export function ChatPanel({
  session,
  onStateChange,
  onModeChange,
}: {
  session: SessionData;
  onStateChange: (s: ChemState) => void;
  onModeChange: (m: AssistMode) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(session.messages);
  const [mode, setMode] = useState<AssistMode>(session.assist_mode);
  const [input, setInput] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [lastTools, setLastTools] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const streaming = draft !== null;

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight; // scroll the conversation, never the page
  }, [messages, draft]);

  async function changeMode(m: AssistMode) {
    setMode(m);
    onModeChange(m);
    try {
      await api.updateSession(session.id, { assist_mode: m });
    } catch {
      /* the mode is also sent with the next message */
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;
    setError(null);
    setInput("");
    setLastTools([]);
    const seq = (messages.at(-1)?.seq ?? 0) + 1;
    setMessages((m) => [...m, { seq, role: "user", text, mode, created_at: new Date().toISOString() }]);
    setDraft({ text: "", tools: [] });
    let tools: string[] = [];
    try {
      await api.sendMessage(session.id, text, mode, (ev) => {
        if (ev.event === "text_delta") setDraft((d) => (d ? { ...d, text: d.text + ev.data.text } : d));
        else if (ev.event === "tool_call") {
          tools = [...tools, ev.data.name];
          setDraft((d) => (d ? { ...d, tools } : d));
        } else if (ev.event === "state_updated") onStateChange(ev.data.chem_state);
        else if (ev.event === "done") {
          onStateChange(ev.data.chem_state);
          setMessages((m) => [...m, { seq: seq + 1, role: "assistant", text: ev.data.text, mode, created_at: new Date().toISOString() }]);
          setLastTools(tools);
        } else if (ev.event === "error") setError(ev.data.message);
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha de conexão com o tutor.");
    } finally {
      setDraft(null);
    }
  }

  return (
    <section className="flex h-[calc(100vh-8rem)] flex-col rounded-lg border border-line bg-card">
      <div className="border-b border-line p-3">
        <ModeSelector mode={mode} onChange={changeMode} disabled={streaming} />
      </div>
      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && !draft && (
          <p className="rounded-md bg-paper p-3 text-sm text-muted">
            Comece descrevendo o que você observa: quantos sinais há, onde estão e o que a fórmula molecular sugere.
          </p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={`${m.seq}-${i}`} className="ml-8 rounded-lg bg-accent-soft px-3 py-2 text-sm">
              {m.text}
            </div>
          ) : (
            <div key={`${m.seq}-${i}`} data-testid="assistant-message" className="chat-md mr-4 text-sm">
              {i === messages.length - 1 && lastTools.length > 0 && <ToolChips tools={lastTools} />}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
            </div>
          ),
        )}
        {draft && (
          <div className="chat-md mr-4 text-sm" aria-live="polite">
            <ToolChips tools={draft.tools} />
            {draft.text ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{draft.text}</ReactMarkdown> : <p className="text-muted">Pensando…</p>}
          </div>
        )}
        {error && <p className="rounded-md bg-bad-soft p-2 text-sm text-bad">{error}</p>}
      </div>
      <form onSubmit={send} className="flex gap-2 border-t border-line p-3">
        <textarea
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
          rows={2}
          maxLength={4000}
          placeholder="Escreva sua observação ou hipótese…"
          className="flex-1 resize-none rounded-md border border-line bg-paper px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="self-end rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}

function ToolChips({ tools }: { tools: string[] }) {
  if (!tools.length) return null;
  return (
    <div className="mb-1 flex flex-wrap gap-1">
      {tools.map((t, i) => (
        <span key={`${t}-${i}`} data-testid="tool-chip" className="rounded-full bg-paper px-2 py-0.5 font-mono text-[11px] text-muted">
          {toolLabel(t)}
        </span>
      ))}
    </div>
  );
}
