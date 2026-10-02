"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";

/** Visible notice while the backend runs the deterministic FakeLLM instead of Claude. */
export function SimulatedTutorBanner() {
  const [simulated, setSimulated] = useState(false);

  useEffect(() => {
    api
      .health()
      .then((h) => setSimulated(h.tutor === "simulated"))
      .catch(() => setSimulated(false));
  }, []);

  if (!simulated) return null;
  return (
    <div data-testid="simulated-banner" className="border-b border-warn/40 bg-warn-soft px-4 py-2 text-center text-sm text-warn">
      Demonstração com <strong>tutor simulado</strong>: as respostas seguem um roteiro fixo e não vêm do Claude. A
      interface, os dados e as checagens de estrutura funcionam normalmente.
    </div>
  );
}
