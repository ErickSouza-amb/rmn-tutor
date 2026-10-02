"use client";

import { api } from "@/lib/api";
import type { StructureCheck } from "@/lib/types";
import { useState } from "react";

const ICON = { pass: "✓", fail: "✗", inconclusive: "?" } as const;
const STYLE = { pass: "text-accent", fail: "text-bad", inconclusive: "text-warn" } as const;
const NAME: Record<string, string> = {
  formula: "Fórmula molecular",
  h_count: "Total de H × integrais",
  environment_count: "Ambientes de H × sinais",
  environment_integrals: "H por ambiente × integrais",
  shift_ranges: "Faixas de deslocamento",
};

export function StructureCheckBox({ sessionId, onChecked }: { sessionId: string; onChecked: () => void }) {
  const [smiles, setSmiles] = useState("");
  const [result, setResult] = useState<StructureCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await api.structureCheck(sessionId, smiles.trim()));
      onChecked();
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-lg border border-line bg-card p-4 text-sm">
      <h2 className="font-semibold">Propor estrutura (SMILES)</h2>
      <form onSubmit={check} className="flex gap-2">
        <input
          data-testid="smiles-input"
          value={smiles}
          onChange={(e) => setSmiles(e.target.value)}
          placeholder="ex.: CCOC(C)=O"
          maxLength={300}
          className="flex-1 rounded-md border border-line bg-paper px-3 py-1.5 font-mono"
        />
        <button
          type="submit"
          disabled={busy || !smiles.trim()}
          className="rounded-md border border-accent px-3 py-1.5 text-accent hover:bg-accent-soft disabled:opacity-50"
        >
          Verificar estrutura
        </button>
      </form>
      {error && <p className="text-bad">{error}</p>}
      {result && (
        <div className="space-y-2">
          <p className="font-mono text-xs text-muted">
            {result.canonical_smiles} · {result.formula} · {result.total_h} H
          </p>
          {result.matches_answer !== undefined && (
            <p className={result.matches_answer ? "font-medium text-accent" : "font-medium text-bad"}>
              {result.matches_answer ? "É a estrutura do exercício." : "Não é a estrutura do exercício."}
            </p>
          )}
          <ul className="space-y-1">
            {result.checks.map((c) => (
              <li key={c.name} data-testid={`check-${c.name}`} className="flex gap-2">
                <span className={`w-4 font-bold ${STYLE[c.status]}`}>{ICON[c.status]}</span>
                <span>
                  <span className="font-medium">{NAME[c.name] ?? c.name}</span>
                  {c.heuristic && <span className="ml-1 text-xs text-muted">(heurística)</span>}: {c.detail}
                </span>
              </li>
            ))}
          </ul>
          <details className="text-xs text-muted">
            <summary>Limitações</summary>
            <ul className="list-disc pl-5">
              {result.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
