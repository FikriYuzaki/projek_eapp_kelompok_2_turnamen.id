"""Supabase client factory for online mode (`APP_MODE=supabase`).

SECURITY RULE:
Never configure or distribute `service_role` keys inside the desktop client.
Always use the publishable/anon key together with user authentication and RLS.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import AppConfig


def create_supabase_client(config: AppConfig) -> Any:
    """Create a Supabase Python SDK client when `APP_MODE=supabase` is configured."""
    if not config.supabase_url or not config.supabase_anon_key:
        raise RuntimeError(
            "Konfigurasi SUPABASE_URL dan SUPABASE_ANON_KEY belum tersedia di .env."
        )

    try:
        from supabase import create_client
        from supabase._sync import client as sync_client_mod

        # Support both legacy JWT format (eyJ...) and new Supabase publishable key format (sb_publishable_...)
        if config.supabase_anon_key.startswith("sb_publishable_"):
            orig_match = sync_client_mod.re.match

            def _allow_publishable_key(pattern: Any, string: str, *args: Any, **kwargs: Any) -> Any:
                if isinstance(string, str) and string.startswith("sb_publishable_"):
                    return True
                return orig_match(pattern, string, *args, **kwargs)

            sync_client_mod.re.match = _allow_publishable_key
    except ImportError as exc:
        raise RuntimeError(
            "Paket 'supabase' belum terpasang. Jalankan 'pip install -r requirements.txt'."
        ) from exc

    return create_client(config.supabase_url, config.supabase_anon_key)
