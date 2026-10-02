import type { ChemState } from "@/lib/types";

const STAGES: { key: string; label: string }[] = [
  { key: "observe", label: "Observação" },
  { key: "evidence", label: "Evidências" },
  { key: "hypothesis", label: "Hipótese" },
  { key: "confront", label: "Confronto" },
  { key: "assemble", label: "Montagem" },
  { key: "check", label: "Checagem" },
];

const STATUS_STYLE: Record<string, string> = {
  open: "border-line text-muted",
  proposed: "border-line text-muted",
  supported: "border-accent text-accent",
  rejected: "border-bad text-bad line-through",
};
const STATUS_LABEL: Record<string, string> = {
  open: "em aberto",
  proposed: "proposta",
  supported: "apoiada",
  rejected: "rejeitada",
};

export function StatePanel({ state }: { state: ChemState }) {
  return (
    <section className="space-y-3 rounded-lg border border-line bg-card p-4 text-sm">
      <h2 className="font-semibold">Quadro de raciocínio</h2>
      <ol className="flex flex-wrap gap-1">
        {STAGES.map((s) => (
          <li
            key={s.key}
            aria-current={state.stage === s.key ? "step" : undefined}
            className={`rounded px-2 py-0.5 text-xs ${state.stage === s.key ? "bg-accent text-white" : "bg-paper text-muted"}`}
          >
            {s.label}
          </li>
        ))}
      </ol>
      <div>
        <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Hipóteses</h3>
        {state.hypotheses.length === 0 ? (
          <p className="text-muted">Nenhuma hipótese registrada ainda.</p>
        ) : (
          <ul className="space-y-1">
            {state.hypotheses.map((h) => (
              <li key={h.id} className="flex items-start gap-2">
                <span className={`rounded border px-1.5 text-xs ${STATUS_STYLE[h.status] ?? ""}`}>{STATUS_LABEL[h.status] ?? h.status}</span>
                <span>{h.text}</span>
                {h.evidence.length > 0 && <span className="font-mono text-xs text-muted">({h.evidence.join(", ")})</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {state.signal_notes.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Sinais</h3>
          <ul className="space-y-0.5">
            {state.signal_notes.map((n) => (
              <li key={n.peak_id}>
                <span className="font-mono">{n.peak_id}</span> — {n.interpretation}{" "}
                <span className="text-xs text-muted">({STATUS_LABEL[n.status] ?? n.status})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {state.unresolved.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted">Não resolvido</h3>
          <ul className="list-disc pl-5">
            {state.unresolved.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-muted">Dicas usadas: {state.hints_given}</p>
    </section>
  );
}
