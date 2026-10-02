"use client";

import { api } from "@/lib/api";
import { MULTIPLICITIES, type Multiplicity, type ParseResult, type Peak } from "@/lib/types";
import { useState } from "react";

function parseNumber(text: string): number | null {
  const t = text.trim().replace(",", ".");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function parseJ(text: string): number[] | null {
  const values = text
    .split(/[;\s]+/)
    .map((v) => parseNumber(v))
    .filter((v): v is number => v !== null);
  return values.length ? values : null;
}

function formatJ(j: number[] | null): string {
  return j ? j.join("; ") : "";
}

function nextId(peaks: Peak[]): string {
  const max = peaks.reduce((m, p) => Math.max(m, Number(p.id.slice(1)) || 0), 0);
  return `P${max + 1}`;
}

export function PeakTableEditor({
  peaks,
  onChange,
  parse = api.parsePeaks,
}: {
  peaks: Peak[];
  onChange: (peaks: Peak[]) => void;
  parse?: (text: string) => Promise<ParseResult>;
}) {
  const [paste, setPaste] = useState("");
  const [errors, setErrors] = useState<ParseResult["errors"]>([]);
  const [busy, setBusy] = useState(false);
  const [jDrafts, setJDrafts] = useState<Record<string, string>>({});

  const update = (id: string, patch: Partial<Peak>) => onChange(peaks.map((p) => (p.id === id ? { ...p, ...patch } : p)));

  async function interpret() {
    setBusy(true);
    try {
      const result = await parse(paste);
      setErrors(result.errors);
      if (result.peaks.length) {
        setJDrafts({});
        onChange(result.peaks);
      }
    } catch (e) {
      setErrors([{ line: 0, message: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  const cell = "w-full rounded border border-line bg-card px-2 py-1 font-mono text-sm";
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <textarea
          data-testid="peak-paste"
          className="w-full rounded-md border border-line bg-card px-3 py-2 font-mono text-sm"
          rows={4}
          value={paste}
          onChange={(e) => setPaste(e.target.value)}
          placeholder={"Cole a lista de picos. Exemplos:\n4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H)\n1.26;3;t;7.1"}
        />
        <button
          type="button"
          onClick={interpret}
          disabled={busy || !paste.trim()}
          className="rounded-md border border-accent px-3 py-1.5 text-sm text-accent hover:bg-accent-soft disabled:opacity-50"
        >
          Interpretar lista
        </button>
        {errors.length > 0 && (
          <ul className="space-y-0.5 text-sm text-bad">
            {errors.map((e, i) => (
              <li key={i}>{e.line > 0 ? `Linha ${e.line}: ${e.message}` : e.message}</li>
            ))}
          </ul>
        )}
      </div>

      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted">
          <tr>
            <th className="py-1">ID</th>
            <th>δ (ppm)</th>
            <th>Integral</th>
            <th>Mult.</th>
            <th>J (Hz)</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {peaks.map((p) => (
            <tr key={p.id} data-testid="peak-row">
              <td className="pr-2 font-mono text-muted">{p.id}</td>
              <td className="pr-2">
                <input
                  aria-label={`δ de ${p.id}`}
                  className={cell}
                  inputMode="decimal"
                  defaultValue={String(p.ppm)}
                  onChange={(e) => {
                    const v = parseNumber(e.target.value);
                    if (v !== null) update(p.id, { ppm: v });
                  }}
                />
              </td>
              <td className="pr-2">
                <input
                  aria-label={`Integral de ${p.id}`}
                  className={cell}
                  inputMode="decimal"
                  defaultValue={p.integral ?? ""}
                  onChange={(e) => update(p.id, { integral: parseNumber(e.target.value) })}
                />
              </td>
              <td className="pr-2">
                <select
                  aria-label={`Multiplicidade de ${p.id}`}
                  className={cell}
                  value={p.multiplicity ?? ""}
                  onChange={(e) => update(p.id, { multiplicity: (e.target.value || null) as Multiplicity | null })}
                >
                  <option value="">—</option>
                  {MULTIPLICITIES.map((m) => (
                    <option key={m} value={m}>
                      {m === "br_s" ? "br s" : m}
                    </option>
                  ))}
                </select>
              </td>
              <td className="pr-2">
                <input
                  aria-label={`J de ${p.id}`}
                  className={cell}
                  value={jDrafts[p.id] ?? formatJ(p.j_hz)}
                  onChange={(e) => {
                    setJDrafts({ ...jDrafts, [p.id]: e.target.value });
                    update(p.id, { j_hz: parseJ(e.target.value) });
                  }}
                />
              </td>
              <td>
                <button
                  type="button"
                  aria-label={`Remover ${p.id}`}
                  onClick={() => onChange(peaks.filter((x) => x.id !== p.id))}
                  className="text-muted hover:text-bad"
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={() =>
          onChange([...peaks, { id: nextId(peaks), ppm: 1.0, integral: null, multiplicity: null, j_hz: null, source: "user", note: null }])
        }
        className="text-sm text-accent hover:underline"
      >
        + Adicionar pico
      </button>
    </div>
  );
}
