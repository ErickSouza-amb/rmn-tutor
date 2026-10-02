"use client";

import { api, imageUrl } from "@/lib/api";
import type { Peak, SessionData } from "@/lib/types";
import { useState } from "react";
import { ImageViewer } from "./ImageViewer";
import { PeakTableEditor } from "./PeakTableEditor";
import { SpectrumPlot } from "./SpectrumPlot";

export function SpectrumPanel({ session, onSessionChange }: { session: SessionData; onSessionChange: (s: SessionData) => void }) {
  const [tab, setTab] = useState<"plot" | "image">(session.peaks.length ? "plot" : "image");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Peak[]>(session.peaks);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const canEdit = !session.exercise;

  async function save() {
    setError(null);
    try {
      const updated = await api.updateSession(session.id, { peaks: draft });
      onSessionChange(updated);
      setDraft(updated.peaks);
      setEditing(false);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const tabBtn = (key: "plot" | "image", label: string) => (
    <button
      type="button"
      onClick={() => setTab(key)}
      aria-pressed={tab === key}
      className={`rounded-t px-3 py-1 text-sm ${tab === key ? "bg-card font-medium" : "text-muted"}`}
    >
      {label}
    </button>
  );

  return (
    <section className="space-y-3">
      <div className="flex gap-1 border-b border-line">
        {tabBtn("plot", "Gráfico dos picos")}
        {session.has_image && tabBtn("image", "Imagem enviada")}
      </div>
      <div className="rounded-lg border border-line bg-card p-3">
        {tab === "image" && session.has_image ? (
          <ImageViewer src={imageUrl(session.id)} alt="Espectro de RMN de ¹H" />
        ) : session.peaks.length ? (
          <SpectrumPlot sessionId={session.id} peaks={session.peaks} refreshKey={refreshKey} />
        ) : (
          <p className="text-sm text-muted">Sem lista de picos: o tutor não terá valores numéricos. Adicione os picos abaixo.</p>
        )}
      </div>
      <div className="rounded-lg border border-line bg-card p-3 text-sm">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-semibold">Tabela de picos</h2>
          {canEdit && !editing && (
            <button type="button" onClick={() => setEditing(true)} className="text-accent hover:underline">
              Editar picos
            </button>
          )}
        </div>
        {editing ? (
          <div className="space-y-2">
            <PeakTableEditor peaks={draft} onChange={setDraft} />
            {error && <p className="text-bad">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={save} className="rounded-md bg-accent px-3 py-1.5 text-white">
                Salvar picos
              </button>
              <button
                type="button"
                onClick={() => {
                  setDraft(session.peaks);
                  setEditing(false);
                }}
                className="text-muted"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <table className="w-full font-mono text-xs">
            <thead className="text-left text-muted">
              <tr>
                <th>ID</th>
                <th>δ (ppm)</th>
                <th>Integral</th>
                <th>Mult.</th>
                <th>J (Hz)</th>
              </tr>
            </thead>
            <tbody>
              {session.peaks.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.ppm}</td>
                  <td>{p.integral ?? "—"}</td>
                  <td>{p.multiplicity === "br_s" ? "br s" : (p.multiplicity ?? "—")}</td>
                  <td>{p.j_hz?.join(", ") ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
