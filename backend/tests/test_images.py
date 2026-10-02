import io

import pytest
from PIL import Image

from app.store.images import MAX_DIMENSION, ImageError, normalize_image, sniff_media_type

MAX = 4 * 1024 * 1024


def _img_bytes(fmt: str, size=(64, 32), exif: bool = False) -> bytes:
    img = Image.new("RGB", size, (200, 10, 10))
    buf = io.BytesIO()
    kwargs = {}
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "CameraMaker"  # Make
        kwargs["exif"] = ex.tobytes()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def test_sniff():
    assert sniff_media_type(_img_bytes("PNG")) == "image/png"
    assert sniff_media_type(_img_bytes("JPEG")) == "image/jpeg"
    assert sniff_media_type(_img_bytes("WEBP")) == "image/webp"
    assert sniff_media_type(b"%PDF-1.7 ...") is None


def test_png_roundtrip():
    out, media = normalize_image(_img_bytes("PNG"), MAX)
    assert media == "image/png"
    assert Image.open(io.BytesIO(out)).size == (64, 32)


def test_jpeg_exif_stripped():
    out, media = normalize_image(_img_bytes("JPEG", exif=True), MAX)
    assert media == "image/jpeg"
    assert dict(Image.open(io.BytesIO(out)).getexif()) == {}


def test_webp_becomes_png():
    _, media = normalize_image(_img_bytes("WEBP"), MAX)
    assert media == "image/png"


def test_large_image_is_downscaled():
    out, _ = normalize_image(_img_bytes("PNG", size=(5000, 1000)), MAX)
    assert max(Image.open(io.BytesIO(out)).size) == MAX_DIMENSION


def test_rejects_non_image_and_oversize():
    with pytest.raises(ImageError, match="(?i)formato"):
        normalize_image(b"<html>not an image</html>", MAX)
    with pytest.raises(ImageError, match="(?i)maior que"):
        normalize_image(b"\x89PNG\r\n\x1a\n" + b"0" * 100, 50)


def test_rejects_corrupt_png():
    with pytest.raises(ImageError, match="corrompid"):
        normalize_image(b"\x89PNG\r\n\x1a\n" + b"garbage" * 10, MAX)
