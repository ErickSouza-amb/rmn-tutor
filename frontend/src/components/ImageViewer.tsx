"use client";

import { useRef, useState } from "react";

export function ImageViewer({ src, alt }: { src: string; alt: string }) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const zoom = (factor: number) => setScale((s) => Math.min(8, Math.max(1, s * factor)));

  return (
    <div className="space-y-2">
      <div
        className="relative h-80 cursor-grab overflow-hidden rounded border border-line bg-white active:cursor-grabbing"
        onPointerDown={(e) => {
          drag.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current) setOffset({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y });
        }}
        onPointerUp={() => (drag.current = null)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={alt}
          draggable={false}
          className="h-full w-full select-none object-contain"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
        />
      </div>
      <div className="flex gap-2 text-xs">
        <button type="button" onClick={() => zoom(1.5)} className="rounded border border-line px-2 py-1">
          Ampliar
        </button>
        <button type="button" onClick={() => zoom(1 / 1.5)} className="rounded border border-line px-2 py-1">
          Reduzir
        </button>
        <button
          type="button"
          onClick={() => {
            setScale(1);
            setOffset({ x: 0, y: 0 });
          }}
          className="rounded border border-line px-2 py-1"
        >
          Ajustar
        </button>
        <span className="self-center text-muted">Arraste para mover. A imagem é só contexto visual.</span>
      </div>
    </div>
  );
}
