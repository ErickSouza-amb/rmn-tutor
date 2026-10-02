import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIMENSION = 2048
Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard


class ImageError(ValueError):
    pass


def sniff_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def normalize_image(data: bytes, max_bytes: int) -> tuple[bytes, str]:
    if len(data) > max_bytes:
        raise ImageError(f"Arquivo maior que o limite de {max_bytes / (1024 * 1024):.0f} MB.")
    media = sniff_media_type(data)
    if media is None:
        raise ImageError("Formato não suportado. Envie PNG, JPEG ou WebP.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ImageError("Imagem corrompida ou inválida.") from exc
    img = ImageOps.exif_transpose(img)
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    out = io.BytesIO()
    if media == "image/jpeg":
        img.convert("RGB").save(out, "JPEG", quality=90)
        return out.getvalue(), "image/jpeg"
    if img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA")
    img.save(out, "PNG", optimize=True)
    return out.getvalue(), "image/png"
