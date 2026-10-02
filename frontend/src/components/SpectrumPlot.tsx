"use client";

import { api } from "@/lib/api";
import type { Peak, Spectrum } from "@/lib/types";
import { useEffect, useRef, useState } from "react";

export function SpectrumPlot({ sessionId, peaks, refreshKey }: { sessionId: string; peaks: Peak[]; refreshKey: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [spectrum, setSpectrum] = useState<Spectrum | null>(null);
  const [range, setRange] = useState<[number, number] | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSpectrum(sessionId).then(setSpectrum).catch((e) => setError(e.message));
  }, [sessionId, refreshKey]);

  useEffect(() => {
    const el = ref.current;
    if (!spectrum || !el) return;
    let disposed = false;
    import("plotly.js-dist-min").then(async ({ default: Plotly }) => {
      if (disposed) return;
      const gd = await Plotly.react(
        el,
        [
          {
            x: spectrum.x,
            y: spectrum.y,
            type: "scatter",
            mode: "lines",
            line: { color: "#1c2430", width: 1 },
            hovertemplate: "δ %{x:.3f} ppm<extra></extra>",
          },
        ],
        {
          margin: { l: 10, r: 10, t: 20, b: 40 },
          height: 320,
          xaxis: { autorange: "reversed", title: { text: "δ (ppm)" }, zeroline: false },
          yaxis: { visible: false, fixedrange: true, range: [-0.03, 1.15] },
          dragmode: "zoom",
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          showlegend: false,
          annotations: peaks.map((p) => ({ x: p.ppm, y: 1.08, text: p.id, showarrow: false, font: { size: 10, color: "#0f766e" } })),
        },
        { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["select2d", "lasso2d", "toImage"] },
      );
      gd.removeAllListeners?.("plotly_click");
      gd.removeAllListeners?.("plotly_relayout");
      gd.on("plotly_click", (ev) => {
        const x = ev.points?.[0]?.x;
        if (typeof x === "number") setPicked(x);
      });
      gd.on("plotly_relayout", (ev) => {
        const a = ev["xaxis.range[0]"];
        const b = ev["xaxis.range[1]"];
        if (a !== undefined && b !== undefined) setRange([Number(a), Number(b)]);
        else if (ev["xaxis.autorange"]) setRange(null);
      });
    });
    return () => {
      disposed = true;
      import("plotly.js-dist-min").then(({ default: Plotly }) => Plotly.purge(el));
    };
  }, [spectrum, peaks]);

  const lo = range ? Math.min(...range) : null;
  const hi = range ? Math.max(...range) : null;
  const visible = lo !== null && hi !== null ? peaks.filter((p) => p.ppm >= lo && p.ppm <= hi) : null;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-bad">{error}</p>}
      <div ref={ref} data-testid="spectrum-plot" className="w-full" />
      <div className="flex flex-wrap gap-4 font-mono text-xs text-muted">
        <span>Arraste para ampliar uma região · duplo clique para voltar</span>
        {picked !== null && <span>δ selecionado: {picked.toFixed(3)} ppm</span>}
        {visible && lo !== null && hi !== null && (
          <span>
            Região {hi.toFixed(2)}–{lo.toFixed(2)} ppm: {visible.length ? visible.map((p) => p.id).join(", ") : "nenhum pico"}
          </span>
        )}
      </div>
      {spectrum?.warnings.map((w) => (
        <p key={w} className="text-xs text-warn">
          {w}
        </p>
      ))}
      <p className="text-xs text-muted">Curva simulada a partir da tabela de picos (didática), não é o FID original.</p>
    </div>
  );
}
