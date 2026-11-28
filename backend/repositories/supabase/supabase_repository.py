"""Supabase PostgreSQL repository adapter implementing `DataStoreRepositoryProtocol`.

Owner: Habil (Database & Authentication Developer)
Note: Active only when `APP_MODE=supabase` is configured with valid credentials.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from backend.contracts.dtos import TOURNAMENT_STATUSES
from backend.core.config import AppConfig
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.infrastructure.supabase.client import (
    create_supabase_client,
    get_current_access_token,
    use_access_token,
)
from backend.modules.tournaments.artwork_validator import (
    GAME_ARTWORK_BUCKET,
    build_supabase_artwork_public_url,
    is_valid_artwork_storage_path,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

logger = logging.getLogger(__name__)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _extract_single_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        return dict(data[0]) if data else None
    if isinstance(data, dict):
        return dict(data)
    return None


def _raise_domain_error_from_postgrest(exc: Exception, context: str) -> None:
    """Translate PostgREST / PostgreSQL error codes into Turnamen.in domain exceptions."""
    if isinstance(
        exc,
        (
            DomainConflictError,
            DomainForbiddenError,
            DomainNotFoundError,
            DomainUnauthorizedError,
            DomainValidationError,
        ),
    ):
        raise exc

    code = str(getattr(exc, "code", "") or "")
    message = str(getattr(exc, "message", "") or str(exc))
    lower_msg = message.lower()

    if code in ("23505", "P0009") or "duplicate key" in lower_msg or "unique constraint" in lower_msg:
        raise DomainConflictError(
            message if code == "P0009" and message else f"Data duplikat pada operasi {context}.",
            {"reason": code or "unique_violation"},
        ) from exc
    if code in ("23503", "P0002") or "foreign key constraint" in lower_msg or "tidak ditemukan" in lower_msg:
        raise DomainNotFoundError(
            f"Referensi entitas terkait tidak ditemukan pada operasi {context}.",
            {"reason": code or "not_found"},
        ) from exc
    if (
        code == "42501"
        or "row-level security" in lower_msg
        or "privilege escalation" in lower_msg
        or "immutable field" in lower_msg
        or "permission denied" in lower_msg
        or "cannot be modified" in lower_msg
    ):
        raise DomainForbiddenError(
            f"Akses ditolak oleh kebijakan keamanan database pada operasi {context}.",
            {"reason": code or "rls_denied"},
        ) from exc
    if (
        code in ("22P02", "22023", "23514")
        or "invalid input syntax" in lower_msg
        or "check constraint" in lower_msg
        or "harus berupa json array" in lower_msg
        or "tidak boleh bernilai null" in lower_msg
    ):
        raise DomainValidationError(
            f"Data tidak memenuhi aturan validasi skema pada operasi {context}.",
            {"reason": code or "check_violation"},
        ) from exc
    raise exc


class SupabaseDataStoreRepository(DataStoreRepositoryProtocol):
    """Production repository backed by Supabase PostgreSQL Data API, Auth, and RLS."""

    is_supabase_mode: bool = True

    def __init__(
        self,
        config: AppConfig,
        client_factory: Callable[..., Any] | None = None,
        bound_access_token: str | None = None,
    ) -> None:
        self._config = config
        self._client_factory = client_factory or create_supabase_client
        self._bound_access_token = (
            bound_access_token.strip()
            if isinstance(bound_access_token, str) and bound_access_token.strip()
            else None
        )
        self._client = self._client_factory(config, access_token=self._bound_access_token)
        self._client_cache_lock = threading.Lock()
        self._token_clients: dict[str, tuple[float, Any]] = {}

    def _get_client(self, explicit_token: str | None = None) -> Any:
        """Return a request-scoped Supabase client carrying the active caller's JWT."""
        token = explicit_token or self._bound_access_token or get_current_access_token()
        if isinstance(token, str):
            clean = token.strip()
            if clean and not clean.startswith("tok_"):
                if clean == self._bound_access_token:
                    return self._client
                cache_key = hashlib.sha256(clean.encode("utf-8")).hexdigest()
                now = time.monotonic()
                with self._client_cache_lock:
                    cached = self._token_clients.get(cache_key)
                    if cached and cached[0] > now:
                        return cached[1]
                client = self._client_factory(self._config, access_token=clean)
                with self._client_cache_lock:
                    if len(self._token_clients) >= 32:
                        self._token_clients.clear()
                    self._token_clients[cache_key] = (now + 300.0, client)
                return client
        return self._client

    def for_access_token(self, access_token: str | None) -> SupabaseDataStoreRepository:
        """Create an isolated repository view bound to a specific user JWT without mutating shared state."""
        return SupabaseDataStoreRepository(
            self._config,
            client_factory=self._client_factory,
            bound_access_token=access_token,
        )

    def with_access_token(self, access_token: str | None) -> Any:
        """Context manager binding a user's JWT to repository operations in the current execution flow."""
        return use_access_token(access_token)

    def reset_to_seed(self) -> None:
        raise NotImplementedError(
            "reset_to_seed() hanya diizinkan pada APP_MODE=mock untuk pengujian lokal."
        )

    def auth_sign_up(
        self,
        email: str,
        password: str,
        user_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a user via Supabase GoTrue Auth without storing session globally."""
        auth_client = self._client_factory(self._config)
        try:
            response = auth_client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": user_metadata or {}},
                }
            )
        except Exception as exc:
            msg = str(exc).lower()
            if "already registered" in msg or "already exists" in msg or "duplicate key" in msg:
                raise DomainConflictError("Email atau username sudah terdaftar.", {"email": email}) from exc
            raise DomainValidationError("Gagal mendaftarkan akun pada Supabase Auth.") from exc

        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if not user or not getattr(user, "id", None):
            raise DomainValidationError("Respons registrasi Supabase Auth tidak menyertakan identitas pengguna.")

        access_token = getattr(session, "access_token", None) if session else None
        return {
            "auth_user_id": str(user.id),
            "email": str(getattr(user, "email", None) or email).lower(),
            "access_token": str(access_token) if access_token else None,
            "requires_email_confirmation": not bool(access_token),
        }

    def auth_sign_in(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user credentials against Supabase GoTrue Auth."""
        auth_client = self._client_factory(self._config)
        try:
            response = auth_client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise DomainUnauthorizedError("Email atau password tidak sesuai.") from exc

        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        access_token = getattr(session, "access_token", None) if session else None
        if not user or not getattr(user, "id", None) or not access_token:
            raise DomainUnauthorizedError("Email atau password tidak sesuai.")

        return {
            "auth_user_id": str(user.id),
            "email": str(getattr(user, "email", None) or email).lower(),
            "access_token": str(access_token),
        }

    def auth_get_user(self, access_token: str) -> dict[str, Any] | None:
        """Verify a Supabase JWT access token and return the authenticated user identity."""
        clean_token = (access_token or "").strip()
        if not clean_token or clean_token.startswith("tok_"):
            return None
        auth_client = self._get_client(clean_token)
        try:
            response = auth_client.auth.get_user(clean_token)
        except Exception:
            cache_key = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
            with self._client_cache_lock:
                self._token_clients.pop(cache_key, None)
            return None

        user = getattr(response, "user", None)
        if not user or not getattr(user, "id", None):
            return None
        return {
            "auth_user_id": str(user.id),
            "email": str(getattr(user, "email", None) or "").lower(),
        }

    def auth_sign_out(self, access_token: str) -> bool:
        """Invalidate the caller's session on Supabase Auth using a request-scoped client."""
        clean_token = (access_token or "").strip()
        if not clean_token or clean_token.startswith("tok_"):
            return False
        cache_key = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
        with self._client_cache_lock:
            self._token_clients.pop(cache_key, None)
        scoped_client = self._client_factory(self._config, access_token=clean_token)
        try:
            scoped_client.auth.sign_out()
            return True
        except Exception as exc:
            logger.warning("Gagal melakukan sign_out pada Supabase Auth: %s", type(exc).__name__)
            return False

    def auth_request_password_recovery(
        self, email: str, redirect_to: str | None = None
    ) -> dict[str, Any]:
        """Trigger a Supabase Auth password recovery email via GoTrue without service_role."""
        auth_client = self._client_factory(self._config)
        options: dict[str, Any] = {}
        if redirect_to:
            options["redirect_to"] = redirect_to
        try:
            auth_client.auth.reset_password_for_email(email, options)
        except Exception as exc:
            msg = str(exc).lower()
            if "rate limit" in msg or "too many requests" in msg or "429" in msg:
                raise DomainValidationError(
                    "Permintaan pemulihan password terlalu sering. Tunggu beberapa saat sebelum mencoba lagi."
                ) from exc
            raise DomainValidationError(
                "Gagal mengirim permintaan pemulihan password ke Supabase Auth."
            ) from exc
        return {"recovery_requested": True}

    def auth_update_password(
        self,
        *,
        new_password: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_hash: str | None = None,
    ) -> dict[str, Any]:
        """Update the user's password via Supabase Auth update_user() without touching profiles."""
        clean_access = (access_token or "").strip()
        clean_refresh = (refresh_token or "").strip()
        clean_hash = (token_hash or "").strip()
        if (clean_access and clean_access.startswith("tok_")) or (
            not clean_access and not clean_hash
        ):
            raise DomainUnauthorizedError(
                "Token pemulihan password tidak ditemukan atau tidak valid."
            )
        if clean_access and not clean_hash and clean_access.count(".") != 2:
            raise DomainUnauthorizedError(
                "Format token pemulihan password tidak valid."
            )

        scoped_client = self._client_factory(
            self._config,
            access_token=clean_access or None,
        )
        try:
            if clean_hash:
                scoped_client.auth.verify_otp(
                    {"token_hash": clean_hash, "type": "recovery"}
                )
            else:
                # Hydrate in-memory GoTrue session because persist_session=False requires it for update_user().
                scoped_client.auth.set_session(clean_access, clean_refresh)

            response = scoped_client.auth.update_user({"password": new_password})
        except (
            DomainUnauthorizedError,
            DomainValidationError,
            DomainForbiddenError,
        ):
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if any(
                hint in msg
                for hint in ("expired", "invalid", "session", "jwt", "unauthorized", "token")
            ):
                raise DomainUnauthorizedError(
                    "Tautan atau token pemulihan password tidak valid atau sudah kedaluwarsa. "
                    "Silakan minta email pemulihan baru."
                ) from exc
            if "same password" in msg or "different from the old password" in msg:
                raise DomainValidationError(
                    "Password baru harus berbeda dari password sebelumnya.",
                    {"field": "new_password"},
                ) from exc
            if any(hint in msg for hint in ("password", "weak", "length", "characters")):
                raise DomainValidationError(
                    "Password baru belum memenuhi kebijakan keamanan Supabase Auth.",
                    {"field": "new_password"},
                ) from exc
            raise DomainValidationError(
                "Gagal memperbarui password pada Supabase Auth."
            ) from exc

        user = getattr(response, "user", None)
        if not user or not getattr(user, "id", None):
            raise DomainValidationError(
                "Respons pembaruan password Supabase Auth tidak valid."
            )
        return {
            "auth_user_id": str(user.id),
            "password_updated": True,
        }

    def list_profiles(self) -> list[dict[str, Any]]:
        client = self._get_client()
        try:
            resp = client.table("profiles").select("*").execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_profiles")
        return [dict(p) for p in (resp.data or [])]

    def get_profile_by_id(self, profile_id: str) -> dict[str, Any] | None:
        if not _is_uuid(profile_id):
            return None
        client = self._get_client()
        try:
            resp = client.table("profiles").select("*").eq("id", profile_id).limit(1).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_profile_by_id")
        return dict(resp.data[0]) if resp.data else None

    def get_public_profile_summary(
        self,
        profile_id: str,
        team_id: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        del actor_id  # Caller identity is always derived inside PostgreSQL from auth.uid().
        if team_id is not None and not _is_uuid(team_id):
            raise DomainForbiddenError(
                "Team Captain hanya dapat mencari profil anggota untuk tim yang valid."
            )
        target_is_uuid = _is_uuid(profile_id)
        client = self._get_client()
        try:
            resp = client.rpc(
                "get_public_profile_summary",
                {
                    "p_profile_id": profile_id if target_is_uuid else None,
                    "p_team_id": team_id,
                },
            ).execute()
        except Exception as exc:
            if not target_is_uuid and str(getattr(exc, "code", "") or "") == "22023":
                return None
            _raise_domain_error_from_postgrest(exc, "get_public_profile_summary")
        row = _extract_single_row(getattr(resp, "data", None))
        if not row:
            return None
        return {
            "id": row.get("id"),
            "username": row.get("username"),
            "full_name": row.get("full_name"),
            "avatar_url": row.get("avatar_url"),
        }

    def get_profile_by_auth_user_id(self, auth_user_id: str) -> dict[str, Any] | None:
        if not _is_uuid(auth_user_id):
            return None
        client = self._get_client()
        try:
            resp = (
                client.table("profiles")
                .select("*")
                .eq("auth_user_id", auth_user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_profile_by_auth_user_id")
        return dict(resp.data[0]) if resp.data else None

    def get_profile_by_email(self, email: str) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            resp = (
                client.table("profiles")
                .select("*")
                .eq("email", email.strip().lower())
                .limit(1)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_profile_by_email")
        return dict(resp.data[0]) if resp.data else None

    def get_profile_by_username(self, username: str) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            resp = (
                client.table("profiles")
                .select("*")
                .eq("username", username.strip())
                .limit(1)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_profile_by_username")
        return dict(resp.data[0]) if resp.data else None

    def create_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {k: v for k, v in data.items() if k not in ("password_hash", "access_token")}
        scoped_client = self._get_client(data.get("access_token"))
        try:
            resp = scoped_client.table("profiles").insert(payload).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_profile")
        if not resp.data:
            raise DomainValidationError("Gagal menyimpan profil pengguna baru.")
        return dict(resp.data[0])

    def update_profile(self, profile_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not _is_uuid(profile_id):
            return None
        payload = {
            k: v
            for k, v in data.items()
            if k not in ("id", "password_hash", "access_token")
        }
        if not payload:
            return self.get_profile_by_id(profile_id)
        scoped_client = self._get_client(data.get("access_token"))
        try:
            resp = scoped_client.table("profiles").update(payload).eq("id", profile_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_profile")
        return dict(resp.data[0]) if resp.data else None

    def assign_user_role(self, profile_id: str, new_role: str) -> dict[str, Any] | None:
        if not _is_uuid(profile_id):
            return None
        client = self._get_client()
        try:
            resp = client.rpc(
                "assign_user_role",
                {"p_target_profile_id": profile_id, "p_new_role": new_role},
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "assign_user_role")
        row = _extract_single_row(getattr(resp, "data", None))
        return row

    def _enrich_game_with_artwork(
        self,
        game: dict[str, Any],
        override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(game)
        if override and is_valid_artwork_storage_path(override.get("storage_path")):
            storage_path = str(override["storage_path"])
            public_url = build_supabase_artwork_public_url(self._config.supabase_url, storage_path)
            if public_url:
                enriched["custom_artwork_path"] = storage_path
                enriched["custom_artwork_url"] = public_url
                enriched["custom_artwork_mime_type"] = override.get("mime_type")
                enriched["custom_artwork_width"] = override.get("width")
                enriched["custom_artwork_height"] = override.get("height")
                enriched["custom_artwork_updated_at"] = override.get("updated_at")
                enriched["artwork_source"] = "custom"
                return enriched
        enriched["custom_artwork_path"] = None
        enriched["custom_artwork_url"] = None
        enriched["custom_artwork_mime_type"] = None
        enriched["custom_artwork_width"] = None
        enriched["custom_artwork_height"] = None
        enriched["custom_artwork_updated_at"] = None
        enriched["artwork_source"] = "official"
        return enriched

    @staticmethod
    def _is_missing_override_relation_error(exc: Exception) -> bool:
        code = str(getattr(exc, "code", "") or "").upper()
        msg = str(getattr(exc, "message", "") or str(exc)).lower()
        return (
            code in ("PGRST205", "42P01")
            or "game_artwork_overrides" in msg
            and ("not find" in msg or "does not exist" in msg or "schema cache" in msg)
        )

    def _fetch_artwork_overrides_map(self, client: Any) -> dict[str, dict[str, Any]]:
        try:
            resp = (
                client.table("game_artwork_overrides")
                .select("game_id,storage_path,mime_type,file_size_bytes,width,height,uploaded_by,updated_at")
                .execute()
            )
        except Exception as exc:
            if self._is_missing_override_relation_error(exc):
                logger.warning("Tabel game_artwork_overrides belum tersedia di skema Supabase aktif; fallback ke artwork resmi.")
                return {}
            _raise_domain_error_from_postgrest(exc, "_fetch_artwork_overrides_map")
            return {}
        mapping: dict[str, dict[str, Any]] = {}
        for row in resp.data or []:
            gid = str(row.get("game_id") or "")
            if gid:
                mapping[gid] = dict(row)
        return mapping

    def list_games(
        self,
        include_inactive: bool = False,
        *,
        include_artwork_overrides: bool = True,
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        try:
            query = client.table("games").select("*")
            if not include_inactive:
                query = query.eq("is_active", True)
            resp = query.execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_games")
        rows = list(resp.data or [])
        if not rows or not include_artwork_overrides:
            return [self._enrich_game_with_artwork(g) for g in rows]
        overrides_by_gid = self._fetch_artwork_overrides_map(client)
        return [
            self._enrich_game_with_artwork(g, overrides_by_gid.get(str(g.get("id") or "")))
            for g in rows
        ]

    def get_game_by_id(self, game_id: str) -> dict[str, Any] | None:
        client = self._get_client()
        column = "id" if _is_uuid(game_id) else "slug"
        try:
            resp = client.table("games").select("*").eq(column, game_id).limit(1).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_game_by_id")
        if not resp.data:
            return None
        row = dict(resp.data[0])
        override = self.get_game_artwork_override(str(row["id"]))
        return self._enrich_game_with_artwork(row, override)

    def create_game(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = client.table("games").insert(data).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_game")
        if not resp.data:
            raise DomainForbiddenError("Operasi penambahan cabang game ditolak oleh kebijakan RLS.")
        return self._enrich_game_with_artwork(dict(resp.data[0]))

    def update_game(self, game_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not _is_uuid(game_id):
            return None
        payload = {k: v for k, v in data.items() if k not in ("id", "created_at")}
        if not payload:
            return self.get_game_by_id(game_id)
        client = self._get_client()
        try:
            resp = client.table("games").update(payload).eq("id", game_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_game")
        if not resp.data:
            return None
        row = dict(resp.data[0])
        override = self.get_game_artwork_override(str(row["id"]))
        return self._enrich_game_with_artwork(row, override)

    def get_game_artwork_override(self, game_id: str) -> dict[str, Any] | None:
        if not _is_uuid(game_id):
            return None
        client = self._get_client()
        try:
            resp = (
                client.table("game_artwork_overrides")
                .select("*")
                .eq("game_id", str(game_id))
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if self._is_missing_override_relation_error(exc):
                return None
            _raise_domain_error_from_postgrest(exc, "get_game_artwork_override")
        return dict(resp.data[0]) if resp.data else None

    def upsert_game_artwork_override(
        self, game_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        if not _is_uuid(game_id):
            raise DomainNotFoundError("Data game tidak ditemukan.", {"game_id": game_id})
        client = self._get_client()
        payload = {
            "game_id": str(game_id),
            "storage_path": str(data["storage_path"]),
            "mime_type": str(data["mime_type"]),
            "file_size_bytes": int(data["file_size_bytes"]),
            "width": data.get("width"),
            "height": data.get("height"),
            "uploaded_by": data.get("uploaded_by"),
        }
        try:
            resp = (
                client.table("game_artwork_overrides")
                .upsert(payload, on_conflict="game_id")
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "upsert_game_artwork_override")
        if not resp.data:
            raise DomainForbiddenError("Penyimpanan metadata artwork ditolak oleh kebijakan RLS.")
        return dict(resp.data[0])

    def delete_game_artwork_override(self, game_id: str) -> dict[str, Any] | None:
        if not _is_uuid(game_id):
            return None
        client = self._get_client()
        try:
            resp = (
                client.table("game_artwork_overrides")
                .delete()
                .eq("game_id", str(game_id))
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "delete_game_artwork_override")
        return dict(resp.data[0]) if resp.data else None

    def upload_game_artwork_object(
        self, storage_path: str, file_bytes: bytes, mime_type: str
    ) -> str:
        if not is_valid_artwork_storage_path(storage_path):
            raise DomainValidationError("Path penyimpanan poster tidak valid.", {"storage_path": storage_path})
        client = self._get_client()
        try:
            client.storage.from_(GAME_ARTWORK_BUCKET).upload(
                path=storage_path,
                file=bytes(file_bytes),
                file_options={
                    "content-type": str(mime_type),
                    "cache-control": "31536000",
                    "upsert": "false",
                },
            )
        except Exception as exc:
            msg = str(exc).lower()
            if (
                "row-level security" in msg
                or "unauthorized" in msg
                or "forbidden" in msg
                or "permission" in msg
                or "403" in msg
            ):
                raise DomainForbiddenError(
                    "Unggah poster ditolak oleh kebijakan RLS Supabase Storage.",
                    {"bucket": GAME_ARTWORK_BUCKET},
                ) from exc
            raise DomainValidationError(
                "Gagal mengunggah file poster ke Supabase Storage.",
                {"bucket": GAME_ARTWORK_BUCKET},
            ) from exc
        return storage_path

    def delete_game_artwork_object(self, storage_path: str) -> bool:
        if not is_valid_artwork_storage_path(storage_path):
            return False
        client = self._get_client()
        try:
            client.storage.from_(GAME_ARTWORK_BUCKET).remove([storage_path])
            return True
        except Exception as exc:
            logger.warning("Pembersihan objek storage %s tidak berhasil: %s", storage_path, type(exc).__name__)
            return False

    def _enrich_tournament(
        self,
        tournament: dict[str, Any],
        games_by_id: dict[str, dict[str, Any]] | None = None,
        reg_counts: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(tournament)
        if games_by_id is not None:
            game = games_by_id.get(str(tournament.get("game_id") or ""))
        else:
            game = self.get_game_by_id(str(tournament.get("game_id") or ""))
        enriched["game_name"] = game["name"] if game else "Unknown Game"
        if reg_counts is not None:
            total_regs, approved_regs = reg_counts
        else:
            client = self._get_client()
            try:
                reg_resp = (
                    client.table("registrations")
                    .select("status")
                    .eq("tournament_id", str(tournament["id"]))
                    .execute()
                )
            except Exception as exc:
                _raise_domain_error_from_postgrest(exc, "_enrich_tournament")
            reg_rows = reg_resp.data or []
            total_regs = len(reg_rows)
            approved_regs = sum(1 for r in reg_rows if r.get("status") == "approved")
        enriched["registered_teams_count"] = total_regs
        enriched["approved_teams_count"] = approved_regs
        return enriched

    def list_tournaments(
        self, status: str | None = None, game_id: str | None = None
    ) -> list[dict[str, Any]]:
        if game_id and not _is_uuid(game_id):
            return []
        client = self._get_client()
        query = client.table("tournaments").select("*")
        if status:
            query = query.eq("status", status)
        if game_id:
            query = query.eq("game_id", game_id)
        try:
            resp = query.order("start_date", desc=False).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_tournaments")
        rows = list(resp.data or [])
        if not rows:
            return []

        games_by_id = {str(g["id"]): g for g in self.list_games(include_artwork_overrides=False)}
        tournament_ids = [str(t["id"]) for t in rows if t.get("id")]
        reg_counts_by_tid: dict[str, list[int]] = {tid: [0, 0] for tid in tournament_ids}
        if tournament_ids:
            reg_query = client.table("registrations").select("tournament_id,status")
            if hasattr(reg_query, "in_"):
                reg_query = reg_query.in_("tournament_id", tournament_ids)
            try:
                reg_resp = reg_query.execute()
            except Exception as exc:
                _raise_domain_error_from_postgrest(exc, "list_tournaments_registrations")
            for reg in reg_resp.data or []:
                tid = str(reg.get("tournament_id") or "")
                bucket = reg_counts_by_tid.get(tid)
                if bucket is not None:
                    bucket[0] += 1
                    if reg.get("status") == "approved":
                        bucket[1] += 1

        return [
            self._enrich_tournament(
                t,
                games_by_id,
                reg_counts=(
                    reg_counts_by_tid.get(str(t.get("id") or ""), [0, 0])[0],
                    reg_counts_by_tid.get(str(t.get("id") or ""), [0, 0])[1],
                ),
            )
            for t in rows
        ]

    def get_tournament_by_id(self, tournament_id: str) -> dict[str, Any] | None:
        client = self._get_client()
        column = "id" if _is_uuid(tournament_id) else "slug"
        try:
            resp = client.table("tournaments").select("*").eq(column, tournament_id).limit(1).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_tournament_by_id")
        if not resp.data:
            return None
        return self._enrich_tournament(resp.data[0])

    def create_tournament(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = client.table("tournaments").insert(data).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_tournament")
        if not resp.data:
            raise DomainForbiddenError("Operasi pembuatan turnamen ditolak oleh kebijakan RLS.")
        return self._enrich_tournament(resp.data[0])

    def update_tournament(
        self, tournament_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not _is_uuid(tournament_id):
            return None
        payload = {k: v for k, v in data.items() if k not in ("id", "created_at")}
        if not payload:
            return self.get_tournament_by_id(tournament_id)
        client = self._get_client()
        try:
            resp = client.table("tournaments").update(payload).eq("id", tournament_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_tournament")
        return self._enrich_tournament(resp.data[0]) if resp.data else None

    def transition_tournament_status(
        self, tournament_id: str, new_status: str
    ) -> dict[str, Any] | None:
        if new_status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(
                f"Status turnamen '{new_status}' tidak valid.", {"field": "status"}
            )
        if not _is_uuid(tournament_id):
            return None
        client = self._get_client()
        try:
            resp = client.rpc(
                "transition_tournament_status",
                {"p_tournament_id": tournament_id, "p_new_status": new_status},
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "transition_tournament_status")
        row = _extract_single_row(getattr(resp, "data", None))
        return self._enrich_tournament(row) if row else None

    def delete_tournament(self, tournament_id: str) -> bool:
        if not _is_uuid(tournament_id):
            return False
        client = self._get_client()
        try:
            resp = client.table("tournaments").delete().eq("id", tournament_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "delete_tournament")
        return bool(resp.data)

    def is_staff_assigned(self, tournament_id: str, user_id: str) -> bool:
        if not _is_uuid(tournament_id) or not _is_uuid(user_id):
            return False
        client = self._get_client()
        try:
            resp = (
                client.table("tournament_staff")
                .select("id")
                .eq("tournament_id", tournament_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "is_staff_assigned")
        return bool(resp.data)

    def list_assigned_tournament_ids(self, user_id: str) -> list[str]:
        if not _is_uuid(user_id):
            return []
        client = self._get_client()
        try:
            resp = (
                client.table("tournament_staff")
                .select("tournament_id")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_assigned_tournament_ids")
        return list(
            dict.fromkeys(
                str(row["tournament_id"])
                for row in (resp.data or [])
                if row.get("tournament_id")
            )
        )

    def list_tournament_staff(self, tournament_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(tournament_id):
            return []
        client = self._get_client()
        try:
            resp = client.rpc(
                "list_tournament_staff",
                {"p_tournament_id": tournament_id},
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_tournament_staff")
        return [dict(row) for row in (resp.data or [])]

    def list_committee_candidates(self) -> list[dict[str, Any]]:
        client = self._get_client()
        try:
            resp = client.rpc("list_committee_candidates", {}).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_committee_candidates")
        return [dict(row) for row in (resp.data or [])]

    def add_tournament_staff(
        self, tournament_id: str, user_id: str, staff_role: str = "referee"
    ) -> dict[str, Any]:
        if not _is_uuid(tournament_id) or not _is_uuid(user_id):
            raise DomainValidationError("ID turnamen dan ID panitia harus berupa UUID valid.")
        client = self._get_client()
        try:
            resp = (
                client.table("tournament_staff")
                .insert(
                    {
                        "tournament_id": tournament_id,
                        "user_id": user_id,
                        "staff_role": staff_role,
                    }
                )
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "add_tournament_staff")
        if not resp.data:
            raise DomainForbiddenError("Penugasan panitia ditolak oleh kebijakan RLS.")
        inserted = dict(resp.data[0])
        for row in self.list_tournament_staff(tournament_id):
            if str(row.get("user_id") or "") == str(user_id):
                return row
        return inserted

    def remove_tournament_staff(self, tournament_id: str, user_id: str) -> bool:
        if not _is_uuid(tournament_id) or not _is_uuid(user_id):
            return False
        client = self._get_client()
        try:
            resp = (
                client.table("tournament_staff")
                .delete()
                .eq("tournament_id", tournament_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "remove_tournament_staff")
        return bool(resp.data)

    def _enrich_team(
        self,
        team: dict[str, Any],
        games_by_id: dict[str, dict[str, Any]] | None = None,
        members_list: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(team)
        members = (
            list(members_list)
            if members_list is not None
            else self.list_team_members(str(team["id"]))
        )
        enriched["members"] = members
        enriched["member_count"] = len(members)
        if games_by_id is not None:
            game = games_by_id.get(str(team.get("game_id") or ""))
        else:
            game = self.get_game_by_id(str(team.get("game_id") or ""))
        enriched["game_name"] = game["name"] if game else "Unknown Game"
        return enriched

    def list_teams(self, game_id: str | None = None) -> list[dict[str, Any]]:
        if game_id and not _is_uuid(game_id):
            return []
        client = self._get_client()
        query = client.table("teams").select("*")
        if game_id:
            query = query.eq("game_id", game_id)
        try:
            resp = query.execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_teams")
        team_rows = list(resp.data or [])
        if not team_rows:
            return []

        games_by_id = {str(g["id"]): g for g in self.list_games(include_artwork_overrides=False)}
        team_ids = [str(t["id"]) for t in team_rows if t.get("id")]
        members_by_team: dict[str, list[dict[str, Any]]] = {tid: [] for tid in team_ids}
        if team_ids:
            mem_query = (
                client.table("team_members").select("*").eq("is_active", True)
            )
            if hasattr(mem_query, "in_"):
                mem_query = mem_query.in_("team_id", team_ids)
            try:
                mem_resp = mem_query.execute()
            except Exception as exc:
                _raise_domain_error_from_postgrest(exc, "list_teams_members")
            for member in mem_resp.data or []:
                tid = str(member.get("team_id") or "")
                if tid in members_by_team:
                    members_by_team[tid].append(dict(member))

        return [
            self._enrich_team(
                t,
                games_by_id,
                members_list=members_by_team.get(str(t.get("id") or ""), []),
            )
            for t in team_rows
        ]

    def get_team_by_id(self, team_id: str) -> dict[str, Any] | None:
        if not _is_uuid(team_id):
            return None
        client = self._get_client()
        try:
            resp = client.table("teams").select("*").eq("id", team_id).limit(1).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_team_by_id")
        if not resp.data:
            return None
        return self._enrich_team(resp.data[0])

    def create_team(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = client.table("teams").insert(data).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_team")
        if not resp.data:
            raise DomainForbiddenError("Operasi pembuatan tim ditolak oleh kebijakan RLS.")
        return self._enrich_team(resp.data[0])

    def update_team(self, team_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not _is_uuid(team_id):
            return None
        payload = {k: v for k, v in data.items() if k not in ("id", "created_at")}
        if not payload:
            return self.get_team_by_id(team_id)
        client = self._get_client()
        try:
            resp = client.table("teams").update(payload).eq("id", team_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_team")
        return self._enrich_team(resp.data[0]) if resp.data else None

    def list_team_members(self, team_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(team_id):
            return []
        client = self._get_client()
        try:
            resp = (
                client.table("team_members")
                .select("*")
                .eq("team_id", team_id)
                .eq("is_active", True)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_team_members")
        return list(resp.data or [])

    def add_team_member(self, team_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        payload = {**data, "team_id": team_id}
        try:
            resp = client.table("team_members").insert(payload).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "add_team_member")
        if not resp.data:
            raise DomainForbiddenError("Operasi penambahan anggota tim ditolak oleh kebijakan RLS.")
        return dict(resp.data[0])

    def list_registrations_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(tournament_id):
            return []
        client = self._get_client()
        try:
            resp = (
                client.table("registrations")
                .select("*")
                .eq("tournament_id", tournament_id)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_registrations_by_tournament")

        reg_rows = list(resp.data or [])
        if not reg_rows:
            return []

        team_ids = list({str(r.get("team_id") or "") for r in reg_rows if r.get("team_id")})
        teams_by_id: dict[str, dict[str, Any]] = {}
        if team_ids:
            teams_query = client.table("teams").select("id,name,tag")
            if hasattr(teams_query, "in_"):
                teams_query = teams_query.in_("id", team_ids)
            try:
                teams_resp = teams_query.execute()
            except Exception as exc:
                _raise_domain_error_from_postgrest(exc, "list_registrations_teams")
            teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}

        results: list[dict[str, Any]] = []
        for reg in reg_rows:
            enriched = dict(reg)
            team = teams_by_id.get(str(reg.get("team_id") or ""))
            enriched["team_name"] = team["name"] if team else "Unknown Team"
            enriched["team_tag"] = team["tag"] if team else "---"
            results.append(enriched)
        results.sort(key=lambda r: (r.get("seed_number") or 999, r.get("registered_at") or ""))
        return results

    def get_registration_by_id(self, registration_id: str) -> dict[str, Any] | None:
        if not _is_uuid(registration_id):
            return None
        client = self._get_client()
        try:
            resp = (
                client.table("registrations")
                .select("*")
                .eq("id", registration_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_registration_by_id")
        return dict(resp.data[0]) if resp.data else None

    def create_registration(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = client.table("registrations").insert(data).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_registration")
        if not resp.data:
            raise DomainForbiddenError("Operasi pendaftaran tim ditolak oleh kebijakan RLS.")
        return dict(resp.data[0])

    def register_team_atomic(
        self, tournament_id: str, team_id: str, registered_by: str, notes: str = ""
    ) -> dict[str, Any]:
        if not _is_uuid(tournament_id):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": tournament_id})
        if not _is_uuid(team_id):
            raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": team_id})
        client = self._get_client()
        try:
            resp = client.rpc(
                "register_team_atomic",
                {
                    "p_tournament_id": tournament_id,
                    "p_team_id": team_id,
                    "p_notes": notes,
                },
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "register_team_atomic")
        row = _extract_single_row(getattr(resp, "data", None))
        if not row:
            raise DomainForbiddenError("Operasi pendaftaran tim ditolak oleh kebijakan RLS.")
        return row

    def update_registration_status(
        self, registration_id: str, status: str, verified_by: str, notes: str = ""
    ) -> dict[str, Any] | None:
        if not _is_uuid(registration_id):
            return None
        client = self._get_client()
        try:
            resp = (
                client.table("registrations")
                .update(
                    {
                        "status": status,
                        "verified_by": verified_by,
                        "verified_at": datetime.now(timezone.utc).isoformat(),
                        "notes": notes,
                    }
                )
                .eq("id", registration_id)
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_registration_status")
        return dict(resp.data[0]) if resp.data else None

    def _enrich_match(
        self,
        match: dict[str, Any],
        teams_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(match)
        if teams_by_id is None:
            client = self._get_client()
            teams_resp = client.table("teams").select("id,name,tag").execute()
            teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        team_a = teams_by_id.get(str(match.get("team_a_id") or ""))
        team_b = teams_by_id.get(str(match.get("team_b_id") or ""))
        winner = teams_by_id.get(str(match.get("winner_team_id") or ""))
        enriched["team_a_name"] = (
            team_a["name"]
            if team_a
            else ("BYE" if match.get("status") == "bye" and not team_a else "TBD")
        )
        enriched["team_a_tag"] = team_a["tag"] if team_a else "---"
        enriched["team_b_name"] = (
            team_b["name"]
            if team_b
            else ("BYE" if match.get("status") == "bye" and not team_b else "TBD")
        )
        enriched["team_b_tag"] = team_b["tag"] if team_b else "---"
        enriched["winner_team_name"] = winner["name"] if winner else None
        return enriched

    def list_matches_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(tournament_id):
            return []
        client = self._get_client()
        try:
            resp = (
                client.table("matches")
                .select("*")
                .eq("tournament_id", tournament_id)
                .order("round_number")
                .order("match_number")
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_matches_by_tournament")

        match_rows = list(resp.data or [])
        if not match_rows:
            return []

        team_ids = list(
            {
                str(tid)
                for m in match_rows
                for tid in (m.get("team_a_id"), m.get("team_b_id"), m.get("winner_team_id"))
                if tid
            }
        )
        teams_by_id: dict[str, dict[str, Any]] = {}
        if team_ids:
            teams_query = client.table("teams").select("id,name,tag")
            if hasattr(teams_query, "in_"):
                teams_query = teams_query.in_("id", team_ids)
            try:
                teams_resp = teams_query.execute()
            except Exception as exc:
                _raise_domain_error_from_postgrest(exc, "list_matches_teams")
            teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        return [self._enrich_match(m, teams_by_id) for m in match_rows]

    def get_match_by_id(self, match_id: str) -> dict[str, Any] | None:
        if not _is_uuid(match_id):
            return None
        client = self._get_client()
        try:
            resp = client.table("matches").select("*").eq("id", match_id).limit(1).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "get_match_by_id")
        if not resp.data:
            return None
        return self._enrich_match(resp.data[0])

    def replace_tournament_matches(
        self, tournament_id: str, matches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Atomically replace bracket matches for a tournament using PostgreSQL RPC transaction."""
        if not tournament_id or not isinstance(tournament_id, str):
            raise DomainValidationError(
                "Parameter 'tournament_id' wajib diisi.",
                {"field": "tournament_id"},
            )
        if matches is None or not isinstance(matches, list):
            raise DomainValidationError(
                "Parameter 'matches' wajib berupa JSON array / list.",
                {"field": "matches"},
            )
        if not self.get_tournament_by_id(tournament_id):
            raise DomainNotFoundError("Turnamen tidak ditemukan.", {"tournament_id": tournament_id})

        prepared: list[dict[str, Any]] = []
        for idx, match in enumerate(matches):
            if not isinstance(match, dict) or "round_number" not in match or "match_number" not in match:
                raise DomainValidationError(
                    "Struktur data pertandingan pada bracket tidak valid.",
                    {"index": idx},
                )
            if (
                isinstance(match["round_number"], bool)
                or not isinstance(match["round_number"], int)
                or match["round_number"] < 1
                or isinstance(match["match_number"], bool)
                or not isinstance(match["match_number"], int)
                or match["match_number"] < 1
            ):
                raise DomainValidationError(
                    "Field 'round_number' dan 'match_number' wajib berupa integer positif.",
                    {"index": idx},
                )
            item = dict(match)
            item.setdefault("id", str(uuid.uuid4()))
            item["tournament_id"] = tournament_id
            prepared.append(item)

        client = self._get_client()
        try:
            client.rpc(
                "replace_tournament_matches",
                {"p_tournament_id": tournament_id, "p_matches": prepared},
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "replace_tournament_matches")

        return self.list_matches_by_tournament(tournament_id)

    def update_match(self, match_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not _is_uuid(match_id):
            return None
        payload = {k: v for k, v in data.items() if k not in ("id", "created_at")}
        if not payload:
            return self.get_match_by_id(match_id)
        client = self._get_client()
        try:
            resp = client.table("matches").update(payload).eq("id", match_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "update_match")
        if not resp.data:
            return None
        return self._enrich_match(resp.data[0])

    def record_match_result(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["game_number"] = int(payload.get("game_number", 1))
        payload.setdefault("verified_at", datetime.now(timezone.utc).isoformat())
        client = self._get_client()
        try:
            resp = (
                client.table("match_results")
                .upsert(payload, on_conflict="match_id,game_number")
                .execute()
            )
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "record_match_result")
        if not resp.data:
            raise DomainForbiddenError("Operasi pencatatan hasil pertandingan ditolak oleh kebijakan RLS.")
        return dict(resp.data[0])

    def list_match_results(self, match_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(match_id):
            return []
        client = self._get_client()
        try:
            resp = client.table("match_results").select("*").eq("match_id", match_id).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_match_results")
        return list(resp.data or [])

    def submit_match_result_atomic(
        self,
        *,
        match_id: str,
        score_a: int,
        score_b: int,
        winner_team_id: str,
        notes: str = "",
        force_override: bool = False,
        actor_id: str | None = None,
        game_number: int = 1,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        del actor_id, winner_team_id  # Caller identity & winner are derived atomically in PostgreSQL.
        if not _is_uuid(match_id):
            raise DomainNotFoundError("Pertandingan tidak ditemukan.", {"match_id": match_id})
        client = self._get_client()
        try:
            resp = client.rpc(
                "submit_match_result_atomic",
                {
                    "p_match_id": match_id,
                    "p_score_a": int(score_a),
                    "p_score_b": int(score_b),
                    "p_force_override": bool(force_override),
                    "p_notes": (notes or "").strip(),
                    "p_game_number": int(game_number),
                    "p_idempotency_key": idempotency_key,
                },
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "submit_match_result_atomic")

        raw = getattr(resp, "data", None)
        if isinstance(raw, list):
            payload = dict(raw[0]) if raw else {}
        elif isinstance(raw, dict):
            payload = dict(raw)
        else:
            payload = {}

        if not payload or not payload.get("match"):
            raise DomainForbiddenError(
                "Operasi pengesahan hasil pertandingan ditolak atau tidak mengembalikan data."
            )

        teams_resp = client.table("teams").select("id,name,tag").execute()
        teams_by_id = {str(t["id"]): t for t in (teams_resp.data or [])}
        match_out = self._enrich_match(dict(payload["match"]), teams_by_id)
        raw_next = payload.get("next_match")
        next_out = self._enrich_match(dict(raw_next), teams_by_id) if isinstance(raw_next, dict) else None
        return {
            "match": match_out,
            "next_match": next_out,
            "tournament_status": payload.get("tournament_status"),
            "idempotent_replay": bool(payload.get("idempotent_replay", False)),
        }

    def list_announcements_by_tournament(self, tournament_id: str) -> list[dict[str, Any]]:
        if not _is_uuid(tournament_id):
            return []
        client = self._get_client()
        try:
            resp = client.rpc(
                "list_tournament_announcements",
                {"p_tournament_id": tournament_id},
            ).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_announcements_by_tournament")
        results: list[dict[str, Any]] = []
        for ann in resp.data or []:
            enriched = dict(ann)
            raw_author = str(enriched.get("author_name") or "").strip()
            enriched["author_name"] = raw_author or "Panitia"
            results.append(enriched)
        return results

    def create_announcement(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        try:
            resp = client.table("announcements").insert(data).execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "create_announcement")
        if not resp.data:
            raise DomainForbiddenError("Operasi publikasi pengumuman ditolak oleh kebijakan RLS.")
        return dict(resp.data[0])

    def log_activity(
        self,
        actor_id: str | None,
        tournament_id: str | None,
        entity_type: str,
        entity_id: str | None,
        action: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "actor_id": actor_id,
            "tournament_id": tournament_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "details": details,
        }
        client = self._get_client()
        try:
            resp = client.table("activity_logs").insert(payload).execute()
            if resp.data:
                return dict(resp.data[0])
        except Exception as exc:
            logger.warning(
                "Gagal menyimpan activity_log ke Supabase (action=%s, entity_type=%s): %s",
                action,
                entity_type,
                type(exc).__name__,
            )
        return {
            "id": str(uuid.uuid4()),
            **payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def list_activity_logs(
        self, tournament_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        query = client.table("activity_logs").select("*")
        if tournament_id:
            query = query.eq("tournament_id", tournament_id)
        query = query.order("created_at", desc=True)
        if isinstance(limit, int) and limit > 0 and hasattr(query, "limit"):
            query = query.limit(limit)
        try:
            resp = query.execute()
        except Exception as exc:
            _raise_domain_error_from_postgrest(exc, "list_activity_logs")
        return list(resp.data or [])
