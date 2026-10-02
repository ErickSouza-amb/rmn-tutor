export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;
export const MAX_DIMENSION = 2048;

function toBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Falha ao converter a imagem."))), type, quality),
  );
}

/** Downscale to ≤ 2048 px and ≤ 4 MB (Vercel Functions cap request bodies at 4.5 MB). */
export async function prepareImage(file: File): Promise<{ blob: Blob; name: string }> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size <= MAX_UPLOAD_BYTES) {
    bitmap.close();
    return { blob: file, name: file.name };
  }
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const base = file.name.replace(/\.\w+$/, "");
  const png = await toBlob(canvas, "image/png");
  if (png.size <= MAX_UPLOAD_BYTES) return { blob: png, name: `${base}.png` };
  const jpeg = await toBlob(canvas, "image/jpeg", 0.9);
  if (jpeg.size > MAX_UPLOAD_BYTES) throw new Error("Imagem grande demais mesmo após redução.");
  return { blob: jpeg, name: `${base}.jpg` };
}
