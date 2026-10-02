"use client";

import { ChatPanel } from "@/components/ChatPanel";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { SpectrumPanel } from "@/components/SpectrumPanel";
import { StatePanel } from "@/components/StatePanel";
import { StructureCheckBox } from "@/components/StructureCheckBox";
import { UnreviewedBadge } from "@/components/UnreviewedBadge";
import { api } from "@/lib/api";
import type { SessionData } from "@/lib/types";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const reload = useCallback(() => {
    api.getSession(id).then(setSession).catch((e) => setError(e.message));
  }, [id]);

  useEffect(reload, [reload]);

  if (error) return <p className="rounded-md bg-bad-soft p-3 text-bad">{error}</p>;
  if (!session) return <p className="text-muted">Carregando sessão…</p>;

  const m = session.metadata;
  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold">{session.title}</h1>
            {session.exercise && !session.exercise.reviewed && <UnreviewedBadge />}
          </div>
          <p className="font-mono text-xs text-muted">
            ¹H · {m.frequency_mhz ? `${m.frequency_mhz} MHz` : "frequência não informada"} · {m.solvent ?? "solvente não informado"} ·{" "}
            {m.molecular_formula ?? "fórmula não informada"}
          </p>
          {session.exercise?.notes && <p className="text-xs text-muted">{session.exercise.notes}</p>}
        </div>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(window.location.href);
            setCopied(true);
          }}
          className="rounded-md border border-line px-3 py-1.5 text-xs"
        >
          {copied ? "Link copiado" : "Copiar link da sessão"}
        </button>
      </header>
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-7">
          <SpectrumPanel session={session} onSessionChange={setSession} />
          <StructureCheckBox sessionId={session.id} onChecked={reload} />
          <StatePanel state={session.chem_state} />
        </div>
        <div className="lg:col-span-5">
          <ChatPanel
            key={session.id}
            session={session}
            onStateChange={(chem_state) => setSession((s) => (s ? { ...s, chem_state } : s))}
            onModeChange={(assist_mode) => setSession((s) => (s ? { ...s, assist_mode } : s))}
          />
        </div>
      </div>
      <PrivacyNotice />
    </div>
  );
}
