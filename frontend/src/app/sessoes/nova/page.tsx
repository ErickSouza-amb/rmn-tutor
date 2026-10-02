"use client";

import { ImageDrop } from "@/components/ImageDrop";
import { MetadataForm } from "@/components/MetadataForm";
import { PeakTableEditor } from "@/components/PeakTableEditor";
import { PrivacyNotice } from "@/components/PrivacyNotice";
import { api } from "@/lib/api";
import { prepareImage } from "@/lib/image";
import type { Peak, SessionMetadata } from "@/lib/types";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function NewSessionPage() {
  const router = useRouter();
  const [metadata, setMetadata] = useState<SessionMetadata>({ frequency_mhz: 400, solvent: "CDCl3" });
  const [peaks, setPeaks] = useState<Peak[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file && peaks.length === 0) {
      setError("Envie a imagem do espectro ou informe a lista de picos (de preferência os dois).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { id } = await api.createSession({ metadata, peaks });
      if (file) {
        const { blob, name } = await prepareImage(file);
        await api.uploadImage(id, blob, name);
      }
      router.push(`/sessoes/${id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-4xl space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Novo espectro de ¹H</h1>
        <p className="text-sm text-muted">
          A imagem serve de contexto visual; os valores numéricos usados pelo tutor vêm da lista de picos.
        </p>
      </div>
      <section className="space-y-3">
        <h2 className="font-semibold">1. Metadados</h2>
        <MetadataForm value={metadata} onChange={setMetadata} />
      </section>
      <section className="space-y-3">
        <h2 className="font-semibold">2. Imagem do espectro</h2>
        <ImageDrop file={file} onChange={setFile} />
      </section>
      <section className="space-y-3">
        <h2 className="font-semibold">3. Lista de picos</h2>
        <PeakTableEditor peaks={peaks} onChange={setPeaks} />
      </section>
      {error && <p className="rounded-md bg-bad-soft p-3 text-sm text-bad">{error}</p>}
      <div className="space-y-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-5 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Criando sessão…" : "Começar sessão com o tutor"}
        </button>
        <PrivacyNotice />
      </div>
    </form>
  );
}
