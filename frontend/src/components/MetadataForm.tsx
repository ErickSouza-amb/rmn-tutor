"use client";

import type { SessionMetadata } from "@/lib/types";

const SOLVENTS = ["CDCl3", "DMSO-d6", "D2O", "CD3OD", "C6D6", "acetona-d6"];

export function MetadataForm({ value, onChange }: { value: SessionMetadata; onChange: (m: SessionMetadata) => void }) {
  const set = (patch: Partial<SessionMetadata>) => onChange({ ...value, ...patch });
  const input = "w-full rounded-md border border-line bg-card px-3 py-2 text-sm";
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <label className="space-y-1 text-sm">
        <span className="font-medium">Frequência (MHz)</span>
        <input
          type="number"
          min={1}
          className={input}
          value={value.frequency_mhz ?? ""}
          onChange={(e) => set({ frequency_mhz: e.target.value ? Number(e.target.value) : null })}
          placeholder="400"
        />
      </label>
      <label className="space-y-1 text-sm">
        <span className="font-medium">Solvente</span>
        <input
          list="solvents"
          className={input}
          value={value.solvent ?? ""}
          onChange={(e) => set({ solvent: e.target.value || null })}
          placeholder="CDCl3"
        />
        <datalist id="solvents">
          {SOLVENTS.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </label>
      <label className="space-y-1 text-sm">
        <span className="font-medium">Fórmula molecular</span>
        <input
          className={`${input} font-mono`}
          value={value.molecular_formula ?? ""}
          onChange={(e) => set({ molecular_formula: e.target.value.replace(/\s/g, "") || null })}
          placeholder="C4H8O2"
        />
      </label>
      <label className="space-y-1 text-sm sm:col-span-3">
        <span className="font-medium">Observações (opcional)</span>
        <textarea
          className={input}
          rows={2}
          maxLength={1000}
          value={value.notes ?? ""}
          onChange={(e) => set({ notes: e.target.value || null })}
        />
      </label>
    </div>
  );
}
