"""Binary signature, dimension, and security validator for custom game artwork uploads."""

from __future__ import annotations

import os
import re
import struct
import uuid
from dataclasses import dataclass
from typing import Any

from backend.core.exceptions import DomainValidationError

GAME_ARTWORK_BUCKET = "game-artwork"
MAX_GAME_ARTWORK_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_ARTWORK_WIDTH = 320
MIN_ARTWORK_HEIGHT = 180
MAX_ARTWORK_WIDTH = 4096
MAX_ARTWORK_HEIGHT = 4096
TARGET_ASPECT_RATIO = 16.0 / 9.0
MIN_ASPECT_RATIO = 0.75
MAX_ASPECT_RATIO = 2.6

ALLOWED_ARTWORK_MIME_TYPES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_EXT_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_STORAGE_PATH_RE = re.compile(
    r"^[a-z0-9-]+/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(?:jpe?g|png|webp)$"
)
_SLUG_SAFE_RE = re.compile(r"[^a-z0-9-]+")
_DANGEROUS_TEXT_MARKERS: tuple[bytes, ...] = (
    b"<svg",
    b"<?xml",
    b"<html",
    b"<!doctype",
    b"<script",
)
_JPEG_SOF_MARKERS = frozenset(
    {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
)


@dataclass(frozen=True)
class ValidatedArtwork:
    """Validated image payload metadata produced after binary inspection."""

    raw_bytes: bytes
    mime_type: str
    extension: str
    file_size_bytes: int
    width: int
    height: int
    aspect_ratio: float
    aspect_ratio_warning: str | None


def is_valid_artwork_storage_path(storage_path: Any) -> bool:
    """Verify canonical `<game-slug>/<uuid>.<ext>` storage path without traversal."""
    if not isinstance(storage_path, str):
        return False
    clean = storage_path.strip()
    if not clean or len(clean) > 300:
        return False
    if ".." in clean or "\\" in clean or "://" in clean or clean.startswith("/"):
        return False
    return bool(_STORAGE_PATH_RE.match(clean))


def generate_unique_artwork_path(game_slug: str, extension: str) -> str:
    """Create a collision-free UUID object path inside `game-artwork` bucket."""
    safe_slug = _SLUG_SAFE_RE.sub("-", str(game_slug or "").strip().lower()).strip("-") or "game"
    clean_ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    if clean_ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise DomainValidationError("Ekstensi file poster tidak valid.", {"extension": extension})
    return f"{safe_slug[:64]}/{uuid.uuid4()}{clean_ext}"


def build_supabase_artwork_public_url(supabase_url: str, storage_path: str) -> str | None:
    """Construct a trusted public Supabase Storage URL from project config and `storage_path`."""
    base = str(supabase_url or "").strip().rstrip("/")
    if not base.startswith("https://") or not is_valid_artwork_storage_path(storage_path):
        return None
    return f"{base}/storage/v1/object/public/{GAME_ARTWORK_BUCKET}/{storage_path}"


def build_mock_artwork_public_url(storage_path: str) -> str | None:
    """Construct local Flask asset route URL for validated mock artwork blobs."""
    if not is_valid_artwork_storage_path(storage_path):
        return None
    return f"/api/v1/games/artwork-assets/{storage_path}"


def _normalize_declared_mime(raw_mime: str) -> str:
    cleaned = str(raw_mime or "").strip().lower().split(";")[0].strip()
    if cleaned == "image/jpg":
        return "image/jpeg"
    return cleaned


def _reject_forbidden_signatures(raw_bytes: bytes) -> None:
    if raw_bytes.startswith((b"MZ", b"\x7fELF", b"#!", b"PK\x03\x04", b"%PDF-", b"GIF87a", b"GIF89a")):
        raise DomainValidationError(
            "Format file ditolak: hanya gambar JPEG, PNG, atau WebP yang diperbolehkan.",
            {"reason": "forbidden_binary_signature"},
        )
    head_lower = raw_bytes[:4096].lstrip().lower()
    for marker in _DANGEROUS_TEXT_MARKERS:
        if marker in head_lower:
            raise DomainValidationError(
                "Format SVG, HTML, atau dokumen berbasis skrip tidak diperbolehkan demi keamanan.",
                {"reason": "svg_or_markup_rejected"},
            )


def _parse_png_dimensions(raw_bytes: bytes) -> tuple[int, int]:
    if len(raw_bytes) < 24 or raw_bytes[:8] != b"\x89PNG\r\n\x1a\n" or raw_bytes[12:16] != b"IHDR":
        raise DomainValidationError("Header PNG rusak atau tidak valid.", {"reason": "invalid_png"})
    width, height = struct.unpack(">II", raw_bytes[16:24])
    return int(width), int(height)


def _parse_jpeg_dimensions(raw_bytes: bytes) -> tuple[int, int]:
    if len(raw_bytes) < 4 or raw_bytes[:3] != b"\xff\xd8\xff":
        raise DomainValidationError("Header JPEG rusak atau tidak valid.", {"reason": "invalid_jpeg"})

    idx = 2
    length = len(raw_bytes)
    while idx < length:
        if raw_bytes[idx] != 0xFF:
            idx += 1
            continue
        while idx < length and raw_bytes[idx] == 0xFF:
            idx += 1
        if idx >= length:
            break
        marker = raw_bytes[idx]
        idx += 1
        if marker in (0xD8, 0xD9, 0x00) or (0xD0 <= marker <= 0xD7):
            continue
        if idx + 2 > length:
            break
        seg_len = struct.unpack(">H", raw_bytes[idx : idx + 2])[0]
        if seg_len < 2 or idx + seg_len > length:
            break
        if marker in _JPEG_SOF_MARKERS:
            if seg_len < 7 or idx + 7 > length:
                break
            height, width = struct.unpack(">HH", raw_bytes[idx + 3 : idx + 7])
            return int(width), int(height)
        idx += seg_len

    raise DomainValidationError(
        "Dimensi gambar JPEG tidak dapat dibaca atau file rusak.",
        {"reason": "invalid_jpeg_dimensions"},
    )


def _parse_webp_dimensions(raw_bytes: bytes) -> tuple[int, int]:
    if len(raw_bytes) < 30 or raw_bytes[:4] != b"RIFF" or raw_bytes[8:12] != b"WEBP":
        raise DomainValidationError("Header WebP rusak atau tidak valid.", {"reason": "invalid_webp"})

    chunk_type = raw_bytes[12:16]
    if chunk_type == b"VP8X":
        width = 1 + int.from_bytes(raw_bytes[24:27], "little")
        height = 1 + int.from_bytes(raw_bytes[27:30], "little")
        return width, height
    if chunk_type == b"VP8 ":
        if len(raw_bytes) < 30 or raw_bytes[23:26] != b"\x9d\x01\x2a":
            raise DomainValidationError("Header WebP VP8 rusak.", {"reason": "invalid_webp_vp8"})
        width = struct.unpack("<H", raw_bytes[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", raw_bytes[28:30])[0] & 0x3FFF
        return int(width), int(height)
    if chunk_type == b"VP8L":
        if len(raw_bytes) < 25 or raw_bytes[20] != 0x2F:
            raise DomainValidationError("Header WebP VP8L rusak.", {"reason": "invalid_webp_vp8l"})
        bits = struct.unpack("<I", raw_bytes[21:25])[0]
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return int(width), int(height)

    raise DomainValidationError("Varian WebP tidak dikenali.", {"reason": "unsupported_webp"})


def validate_and_inspect_artwork_upload(
    raw_bytes: bytes,
    *,
    filename: str = "",
    declared_content_type: str = "",
) -> ValidatedArtwork:
    """Validate file size, magic bytes, MIME/extension match, dimensions, and aspect ratio."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) == 0:
        raise DomainValidationError("File gambar poster kosong atau tidak terbaca.", {"field": "file"})

    payload = bytes(raw_bytes)
    size = len(payload)
    if size > MAX_GAME_ARTWORK_BYTES:
        raise DomainValidationError(
            "Ukuran gambar poster melebihi batas maksimal 5 MB.",
            {"max_bytes": MAX_GAME_ARTWORK_BYTES, "file_size_bytes": size},
        )

    _reject_forbidden_signatures(payload)

    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
        width, height = _parse_png_dimensions(payload)
    elif payload.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
        width, height = _parse_jpeg_dimensions(payload)
    elif len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        detected_mime = "image/webp"
        width, height = _parse_webp_dimensions(payload)
    else:
        raise DomainValidationError(
            "Isi file bukan gambar JPEG, PNG, atau WebP yang valid.",
            {"reason": "unrecognized_image_signature"},
        )

    ext = os.path.splitext(str(filename or "").strip().lower())[1]
    if ext:
        expected_mime_for_ext = _EXT_TO_MIME.get(ext)
        if expected_mime_for_ext != detected_mime:
            raise DomainValidationError(
                "Ekstensi file tidak cocok dengan isi file gambar sebenarnya.",
                {"extension": ext, "detected_mime": detected_mime},
            )

    norm_declared = _normalize_declared_mime(declared_content_type)
    if norm_declared and norm_declared not in ("application/octet-stream", detected_mime):
        raise DomainValidationError(
            "Tipe MIME file tidak sesuai dengan signature gambar sebenarnya.",
            {"declared_mime": norm_declared, "detected_mime": detected_mime},
        )

    if (
        width < MIN_ARTWORK_WIDTH
        or height < MIN_ARTWORK_HEIGHT
        or width > MAX_ARTWORK_WIDTH
        or height > MAX_ARTWORK_HEIGHT
    ):
        raise DomainValidationError(
            f"Dimensi gambar harus antara {MIN_ARTWORK_WIDTH}x{MIN_ARTWORK_HEIGHT} hingga "
            f"{MAX_ARTWORK_WIDTH}x{MAX_ARTWORK_HEIGHT} piksel (terdeteksi {width}x{height}).",
            {"width": width, "height": height},
        )

    ratio = round(width / float(height), 3)
    if ratio < MIN_ASPECT_RATIO or ratio > MAX_ASPECT_RATIO:
        raise DomainValidationError(
            f"Rasio aspek gambar ({ratio}:1) terlalu ekstrem untuk poster arena 16:9. "
            "Gunakan gambar lanskap atau sesuaikan proporsi terlebih dahulu.",
            {"width": width, "height": height, "aspect_ratio": ratio},
        )

    ratio_warning = None
    if abs(ratio - TARGET_ASPECT_RATIO) > 0.35:
        ratio_warning = (
            f"Rasio gambar {width}x{height} ({ratio}:1) akan dipotong rapi otomatis ke bingkai 16:9."
        )

    return ValidatedArtwork(
        raw_bytes=payload,
        mime_type=detected_mime,
        extension=_MIME_TO_EXT[detected_mime],
        file_size_bytes=size,
        width=width,
        height=height,
        aspect_ratio=ratio,
        aspect_ratio_warning=ratio_warning,
    )
