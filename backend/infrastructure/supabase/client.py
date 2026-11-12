"""Supabase client factory for online mode (`APP_MODE=supabase`).

SECURITY RULE:
Never configure or distribute `service_role` or secret keys inside the desktop client.
Always use the public `anon` JWT key together with user authentication and RLS.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import urlparse

from backend.core.config import AppConfig

_JWT_PATTERN = re.compile(r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+$")
_PLACEHOLDER_URLS = {
    "https://your-project-ref.supabase.co",
    "http://your-project-ref.supabase.co",
}
_PLACEHOLDER_KEYS = {
    "your-supabase-publishable-or-anon-key",
    "your-supabase-anon-key",
}


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        parsed = json.loads(decoded_bytes.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def validate_supabase_credentials(supabase_url: str, supabase_key: str) -> None:
    """Validate URL and anon key format without logging or exposing secret values."""
    url = (supabase_url or "").strip()
    key = (supabase_key or "").strip()

    if not url or not key:
        raise RuntimeError(
            "Konfigurasi SUPABASE_URL dan SUPABASE_ANON_KEY belum tersedia di .env."
        )

    parsed_url = urlparse(url)
    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
        or url.lower().rstrip("/") in _PLACEHOLDER_URLS
    ):
        raise RuntimeError(
            "Konfigurasi SUPABASE_URL tidak valid. Gunakan URL proyek Supabase yang benar (https://<project-ref>.supabase.co)."
        )

    if key.lower() in _PLACEHOLDER_KEYS:
        raise RuntimeError(
            "Konfigurasi SUPABASE_ANON_KEY masih berisi nilai placeholder. Isi dengan anon public JWT key dari Supabase."
        )

    if key.startswith("sb_secret_") or "service_role" in key.lower():
        raise RuntimeError(
            "Keamanan ditolak: Dilarang menggunakan secret key atau service_role key pada aplikasi desktop Turnamen.in."
        )

    if key.startswith("sb_publishable_"):
        raise RuntimeError(
            "SUPABASE_ANON_KEY menggunakan format 'sb_publishable_*' yang belum didukung oleh SDK supabase==2.7.4 untuk GoTrue Auth. "
            "Salin 'anon' 'public' key berformat JWT ('eyJ...') dari Supabase Dashboard -> Project Settings -> API."
        )

    if not _JWT_PATTERN.match(key):
        raise RuntimeError(
            "Format SUPABASE_ANON_KEY tidak valid. Gunakan 'anon' public key berformat JWT ('eyJ...') dari proyek Supabase."
        )

    claims = _decode_jwt_payload(key)
    role_claim = str(claims.get("role") or "").strip().lower()
    if role_claim == "service_role":
        raise RuntimeError(
            "Keamanan ditolak: SUPABASE_ANON_KEY terdeteksi memiliki klaim role 'service_role'. Gunakan key dengan role 'anon'."
        )


def create_supabase_client(
    config: AppConfig,
    access_token: str | None = None,
) -> Any:
    """Create a stateless Supabase Python SDK client when `APP_MODE=supabase` is configured."""
    validate_supabase_credentials(config.supabase_url, config.supabase_anon_key)

    try:
        from supabase import ClientOptions, create_client
    except ImportError as exc:
        raise RuntimeError(
            "Paket 'supabase' belum terpasang. Jalankan 'pip install -r requirements.txt'."
        ) from exc

    headers: dict[str, str] = {}
    if access_token:
        clean_token = access_token.strip()
        if clean_token:
            headers["Authorization"] = f"Bearer {clean_token}"

    options = ClientOptions(
        persist_session=False,
        auto_refresh_token=False,
        headers=headers,
    )
    return create_client(config.supabase_url.strip(), config.supabase_anon_key.strip(), options=options)
