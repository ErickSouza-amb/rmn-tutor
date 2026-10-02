"use client";

import { MODE_LABELS, type AssistMode } from "@/lib/types";
import { useState } from "react";

const MODES: AssistMode[] = ["tutor", "hint", "verify", "solution"];

export function ModeSelector({
  mode,
  onChange,
  disabled = false,
}: {
  mode: AssistMode;
  onChange: (m: AssistMode) => void;
  disabled?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  return (
    <div className="space-y-2">
      <div role="group" aria-label="Modo de assistência" className="flex flex-wrap gap-1">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            disabled={disabled}
            aria-pressed={mode === m}
            onClick={() => (m === "solution" ? setConfirming(true) : onChange(m))}
            className={`rounded-full border px-3 py-1 text-xs ${
              mode === m ? "border-accent bg-accent text-white" : "border-line bg-card text-ink hover:border-accent"
            } disabled:opacity-50`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      {confirming && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-warn/40 bg-warn-soft p-2 text-xs text-warn">
          <span>O tutor vai explicar a solução inteira. Tente mais um pouco antes?</span>
          <button
            type="button"
            className="rounded bg-warn px-2 py-1 text-white"
            onClick={() => {
              setConfirming(false);
              onChange("solution");
            }}
          >
            Sim, mostrar a solução
          </button>
          <button type="button" className="underline" onClick={() => setConfirming(false)}>
            Cancelar
          </button>
        </div>
      )}
    </div>
  );
}
