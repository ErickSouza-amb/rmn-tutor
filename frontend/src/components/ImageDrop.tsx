"use client";

import { useEffect, useMemo } from "react";

export function ImageDrop({ file, onChange }: { file: File | null; onChange: (f: File | null) => void }) {
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  return (
    <div className="space-y-2">
      <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-line bg-card p-6 text-sm text-muted hover:border-accent">
        <span className="font-medium text-ink">Imagem do espectro (PNG, JPEG ou WebP)</span>
        <span>Clique para escolher um arquivo. Imagens grandes são reduzidas automaticamente.</span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          data-testid="image-input"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
      </label>
      {preview && (
        <div className="flex items-start gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Pré-visualização do espectro" className="max-h-48 rounded border border-line" />
          <button type="button" onClick={() => onChange(null)} className="text-sm text-muted hover:text-bad">
            Remover imagem
          </button>
        </div>
      )}
    </div>
  );
}
