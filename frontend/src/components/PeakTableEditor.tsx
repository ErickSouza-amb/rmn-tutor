"use client";

import { api } from "@/lib/api";
import { MULTIPLICITIES, type Multiplicity, type ParseResult, type Peak } from "@/lib/types";
import { useState } from "react";

/** Number with dot or Brazilian decimal comma; `undefined` means invalid input, `null` means empty. */
function parseNumber(text: string): number | null | undefined {
  const t = text.trim().replace(/(\d),(\d)/, "$1.$2");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : undefined;
}

function parseIntegral(text: string): number | null | undefined {
  return parseNumber(text.trim().replace(/\s*H$/i, ""));
}

/** Same rule as the backend parser: with dot decimals commas separate values; otherwise only ";", spaces or ", ". */
function parseJ(text: string): number[] | null | undefined {
  const t = text.trim().replace(/\s*Hz$/i, "");
  if (!t) return null;
  const parts = (/\d\.\d/.test(t) ? t.split(/[;,\s]+/) : t.split(/;|\s+|,(?=\s)/)).filter((p) => p !== "");
  const values = parts.map((p) => parseNumber(p));
  if (values.some((v) => v === undefined || v === null)) return undefined;
  return values as number[];
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
  // raw text per cell ("P1:ppm"); the table always shows what the student typed, and invalid cells are flagged
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const draftOf = (id: string, field: string, fallback: string) => drafts[`${id}:${field}`] ?? fallback;
  const isInvalid = (id: string, field: string, parse: (t: string) => unknown) => {
    const raw = drafts[`${id}:${field}`];
    return raw !== undefined && parse(raw) === undefined;
  };
  function editCell<T>(id: string, field: string, text: string, parse: (t: string) => T | undefined, apply: (v: T) => Partial<Peak>) {
    setDrafts((d) => ({ ...d, [`${id}:${field}`]: text }));
    const value = parse(text);
    if (value !== undefined) update(id, apply(value));
  }

  const update = (id: string, patch: Partial<Peak>) => onChange(peaks.map((p) => (p.id === id ? { ...p, ...patch } : p)));

  async function interpret() {
    setBusy(true);
    try {
      const result = await parse(paste);
      setErrors(result.errors);
      if (result.peaks.length) {
        setDrafts({});
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
                  aria-invalid={isInvalid(p.id, "ppm", parseNumber) || drafts[`${p.id}:ppm`] === ""}
                  className={`${cell} aria-[invalid=true]:border-bad`}
                  inputMode="decimal"
                  value={draftOf(p.id, "ppm", String(p.ppm))}
                  onChange={(e) =>
                    editCell(p.id, "ppm", e.target.value, (t) => parseNumber(t) ?? undefined, (v: number) => ({ ppm: v }))
                  }
                />
              </td>
              <td className="pr-2">
                <input
                  aria-label={`Integral de ${p.id}`}
                  aria-invalid={isInvalid(p.id, "integral", parseIntegral)}
                  className={`${cell} aria-[invalid=true]:border-bad`}
                  inputMode="decimal"
                  value={draftOf(p.id, "integral", p.integral === null ? "" : String(p.integral))}
                  onChange={(e) => editCell(p.id, "integral", e.target.value, parseIntegral, (v) => ({ integral: v }))}
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
                  aria-invalid={isInvalid(p.id, "j", parseJ)}
                  className={`${cell} aria-[invalid=true]:border-bad`}
                  value={draftOf(p.id, "j", formatJ(p.j_hz))}
                  onChange={(e) => editCell(p.id, "j", e.target.value, parseJ, (v) => ({ j_hz: v }))}
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
