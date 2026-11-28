"""Authentication and session service for Turnamen.in.

Owner: Habil (Database & Authentication Developer)
Security Rules:
- Self-registration can only assign `player` or `team_captain` roles.
- Online mode (`APP_MODE=supabase`) delegates authentication and JWT verification to Supabase Auth,
  propagates the caller's verified JWT to repository operations via request-scoped context,
  and resolves authorization roles exclusively from `public.profiles.role`.
- Mock mode (`APP_MODE=mock`) uses Werkzeug password hashes and in-memory tokens for offline testing.
"""

from __future__ import annotations

import copy
import hashlib
import re
import secrets
import threading
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from werkzeug.security import check_password_hash, generate_password_hash

from backend.core.config import decode_jwt_payload_unverified

from backend.contracts.dtos import (
    ALL_ROLES,
    ROLE_PLAYER,
    ROLE_SUPER_ADMIN,
    SELF_REGISTRABLE_ROLES,
)
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.infrastructure.supabase.client import (
    bind_request_access_token,
    use_access_token,
)
from backend.modules.auth.permissions import require_authenticated, require_permission
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_MAX_LENGTH = 255
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,60}$")
FULL_NAME_LENGTH = (2, 120)
PHONE_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 256
DEFAULT_RECOVERY_REDIRECT_URL = "http://127.0.0.1:8080/index.html"
ALLOWED_LOCAL_REDIRECT_HOSTS = ("127.0.0.1", "localhost")
PROFILE_NOT_PROVISIONED_MESSAGE = (
    "Akun belum terhubung dengan profil Turnamen.in. Hubungi administrator untuk aktivasi profil."
)


def _validate_recovery_redirect_url(redirect_to: Any) -> str:
    if redirect_to is None:
        return DEFAULT_RECOVERY_REDIRECT_URL
    if not isinstance(redirect_to, str):
        raise DomainValidationError(
            "URL redirect pemulihan harus berupa teks.", {"field": "redirect_to"}
        )
    clean = redirect_to.strip()
    if not clean:
        return DEFAULT_RECOVERY_REDIRECT_URL

    parsed = urlsplit(clean)
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() not in ("http", "https")
        or hostname not in ALLOWED_LOCAL_REDIRECT_HOSTS
        or parsed.username
        or parsed.password
    ):
        raise DomainValidationError(
            "URL redirect pemulihan hanya diizinkan ke aplikasi desktop lokal (127.0.0.1 atau localhost).",
            {"field": "redirect_to"},
        )
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


def _require_text(value: Any, field: str, label: str) -> str:
    if not isinstance(value, str):
        raise DomainValidationError(f"{label} harus berupa teks.", {"field": field})
    return value.strip()


def _validate_full_name(raw: Any) -> str:
    full_name = _require_text(raw, "full_name", "Nama lengkap")
    low, high = FULL_NAME_LENGTH
    if len(full_name) < low or len(full_name) > high:
        raise DomainValidationError(
            f"Nama lengkap harus terdiri dari {low} hingga {high} karakter.",
            {"field": "full_name"},
        )
    return full_name


def _validate_registration_identity(email: str, username: str, full_name: str) -> None:
    if len(email) > EMAIL_MAX_LENGTH or not EMAIL_PATTERN.match(email):
        raise DomainValidationError("Alamat email tidak valid.", {"field": "email"})
    if not USERNAME_PATTERN.match(username):
        raise DomainValidationError(
            "Username harus 3-60 karakter dan hanya berisi huruf, angka, titik, garis bawah, "
            "atau tanda hubung.",
            {"field": "username"},
        )
    _validate_full_name(full_name)


def _sanitize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Strip internal sensitive fields before returning profile data to callers."""
    return {
        k: v
        for k, v in profile.items()
        if k not in ("password_hash", "access_token")
    }


TOKEN_CACHE_TTL_SECONDS = 5.0
TOKEN_CACHE_MAX_ENTRIES = 128


class AuthService:
    """Application service handling registration, login, session lookup, and role security."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository
        self._sessions: dict[str, str] = {}
        self._token_cache_lock = threading.Lock()
        self._verified_token_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def _token_cache_key(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _get_cached_verified_identity(self, token: str) -> dict[str, Any] | None:
        key = self._token_cache_key(token)
        now = time.monotonic()
        with self._token_cache_lock:
            entry = self._verified_token_cache.get(key)
            if not entry:
                return None
            expires_at, verified = entry
            if expires_at <= now:
                self._verified_token_cache.pop(key, None)
                return None
            return dict(verified)

    def _set_cached_verified_identity(self, token: str, verified: dict[str, Any]) -> None:
        ttl = TOKEN_CACHE_TTL_SECONDS
        claims = decode_jwt_payload_unverified(token)
        raw_exp = claims.get("exp") if isinstance(claims, dict) else None
        if isinstance(raw_exp, (int, float)):
            remaining = float(raw_exp) - time.time()
            if remaining <= 0:
                return
            ttl = min(ttl, remaining)
        key = self._token_cache_key(token)
        expires_at = time.monotonic() + ttl
        payload = {
            "auth_user_id": str(verified["auth_user_id"]),
            "email": str(verified.get("email") or ""),
        }
        with self._token_cache_lock:
            if len(self._verified_token_cache) >= TOKEN_CACHE_MAX_ENTRIES:
                self._verified_token_cache.clear()
            self._verified_token_cache[key] = (expires_at, payload)

    def _invalidate_token_cache(self, token: str | None = None) -> None:
        with self._token_cache_lock:
            if token:
                self._verified_token_cache.pop(self._token_cache_key(token), None)
            else:
                self._verified_token_cache.clear()

    @property
    def _is_online_mode(self) -> bool:
        return bool(getattr(self._repo, "is_supabase_mode", False))

    def _find_profile_by_auth_user_id(self, auth_user_id: str) -> dict[str, Any] | None:
        finder = getattr(self._repo, "get_profile_by_auth_user_id", None)
        if callable(finder):
            return finder(auth_user_id)
        for profile in self._repo.list_profiles():
            if profile.get("auth_user_id") == auth_user_id:
                return profile
        return None

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = _require_text(payload.get("email") or "", "email", "Email").lower()
        username = _require_text(payload.get("username") or "", "username", "Username")
        full_name = _require_text(payload.get("full_name") or "", "full_name", "Nama lengkap")
        raw_password = payload.get("password")
        if raw_password is None:
            password = ""
        elif not isinstance(raw_password, str):
            raise DomainValidationError("Password harus berupa teks.", {"field": "password"})
        else:
            password = raw_password

        raw_role = payload.get("role")
        if raw_role is None:
            requested_role = ROLE_PLAYER
        else:
            requested_role = _require_text(raw_role, "role", "Role").lower() or ROLE_PLAYER

        raw_phone = payload.get("phone")
        if raw_phone is None or raw_phone == "":
            phone = None
        else:
            phone = _require_text(raw_phone, "phone", "Nomor telepon") or None
            if phone and len(phone) > PHONE_MAX_LENGTH:
                raise DomainValidationError(
                    f"Nomor telepon maksimal {PHONE_MAX_LENGTH} karakter.", {"field": "phone"}
                )

        _validate_registration_identity(email, username, full_name)
        if not password.strip() or len(password) < 6:
            raise DomainValidationError("Password minimal terdiri dari 6 karakter.", {"field": "password"})

        if requested_role not in ALL_ROLES:
            raise DomainValidationError(f"Role '{requested_role}' tidak dikenali.", {"field": "role"})
        if requested_role not in SELF_REGISTRABLE_ROLES:
            raise DomainForbiddenError(
                f"Pendaftaran mandiri tidak diizinkan memilih role '{requested_role}'. "
                f"Hanya role {SELF_REGISTRABLE_ROLES} yang dapat dipilih saat registrasi.",
                details={"requested_role": requested_role},
            )

        if self._is_online_mode:
            return self._register_supabase(
                email=email,
                username=username,
                full_name=full_name,
                password=password,
                requested_role=requested_role,
                phone=phone,
            )

        if self._repo.get_profile_by_email(email):
            raise DomainConflictError("Email sudah terdaftar.", {"email": email})
        if self._repo.get_profile_by_username(username):
            raise DomainConflictError("Username sudah digunakan.", {"username": username})

        created = self._repo.create_profile(
            {
                "email": email,
                "username": username,
                "full_name": full_name,
                "role": requested_role,
                "phone": phone,
                "password_hash": generate_password_hash(password),
            }
        )
        token = f"tok_{secrets.token_urlsafe(24)}"
        self._sessions[token] = created["id"]
        self._repo.log_activity(
            actor_id=created["id"],
            tournament_id=None,
            entity_type="profile",
            entity_id=created["id"],
            action="USER_REGISTERED",
            details={"role": requested_role, "email": email},
        )
        return {
            "token": token,
            "user": _sanitize_profile(created),
        }

    def _register_supabase(
        self,
        email: str,
        username: str,
        full_name: str,
        password: str,
        requested_role: str,
        phone: str | None,
    ) -> dict[str, Any]:
        sign_up_fn = getattr(self._repo, "auth_sign_up", None)
        if not callable(sign_up_fn):
            raise DomainValidationError("Repository Supabase tidak mendukung operasi auth_sign_up.")

        metadata: dict[str, Any] = {
            "username": username,
            "full_name": full_name,
            "role": requested_role,
        }
        if phone:
            metadata["phone"] = phone

        auth_result = sign_up_fn(
            email=email,
            password=password,
            user_metadata=metadata,
        )
        auth_user_id = str(auth_result["auth_user_id"])
        access_token = auth_result.get("access_token")

        if not access_token:
            return {
                "token": None,
                "requires_email_confirmation": True,
                "user": {
                    "id": auth_user_id,
                    "auth_user_id": auth_user_id,
                    "email": email,
                    "username": username,
                    "full_name": full_name,
                    "role": requested_role,
                    "phone": phone,
                    "avatar_url": None,
                    "is_active": True,
                },
            }

        with use_access_token(access_token):
            # Profiles are linked to auth users only by the provisioning trigger, never by email.
            profile = self._find_profile_by_auth_user_id(auth_user_id)
            if not profile:
                profile = self._repo.create_profile(
                    {
                        "id": auth_user_id,
                        "auth_user_id": auth_user_id,
                        "email": email,
                        "username": username,
                        "full_name": full_name,
                        "role": requested_role,
                        "phone": phone,
                        "is_active": True,
                    }
                )
            elif phone and not profile.get("phone"):
                profile = (
                    self._repo.update_profile(
                        profile["id"],
                        {"phone": phone},
                    )
                    or profile
                )

            self._repo.log_activity(
                actor_id=profile["id"],
                tournament_id=None,
                entity_type="profile",
                entity_id=profile["id"],
                action="USER_REGISTERED",
                details={"role": profile.get("role", requested_role), "email": email},
            )

        bind_request_access_token(access_token)
        return {
            "token": access_token,
            "requires_email_confirmation": False,
            "user": _sanitize_profile(profile),
        }

    def login(self, email: str, password: str) -> dict[str, Any]:
        if not isinstance(email, str) or not isinstance(password, str):
            raise DomainValidationError("Email dan password harus berupa teks.")
        normalized_email = email.strip().lower()
        if not normalized_email or not password:
            raise DomainValidationError("Email dan password wajib diisi.")

        if self._is_online_mode:
            return self._login_supabase(normalized_email, password)

        profile = self._repo.get_profile_by_email(normalized_email)
        if not profile:
            raise DomainUnauthorizedError("Email atau password tidak sesuai.")

        stored_hash = profile.get("password_hash") or ""
        if not stored_hash or not check_password_hash(stored_hash, password):
            raise DomainUnauthorizedError("Email atau password tidak sesuai.")

        if not profile.get("is_active", True):
            raise DomainForbiddenError("Akun pengguna tidak aktif.")

        token = f"tok_{secrets.token_urlsafe(24)}"
        self._sessions[token] = profile["id"]
        return {
            "token": token,
            "user": _sanitize_profile(profile),
        }

    def _login_supabase(self, normalized_email: str, password: str) -> dict[str, Any]:
        sign_in_fn = getattr(self._repo, "auth_sign_in", None)
        if not callable(sign_in_fn):
            raise DomainUnauthorizedError("Layanan autentikasi online tidak tersedia.")

        auth_result = sign_in_fn(normalized_email, password)
        auth_user_id = str(auth_result["auth_user_id"])
        access_token = str(auth_result["access_token"])

        with use_access_token(access_token):
            profile = self._find_profile_by_auth_user_id(auth_user_id)

        if not profile:
            raise DomainUnauthorizedError(
                PROFILE_NOT_PROVISIONED_MESSAGE, {"reason": "profile_not_provisioned"}
            )

        if not profile.get("is_active", True):
            raise DomainForbiddenError("Akun pengguna tidak aktif.")

        bind_request_access_token(access_token)
        self._set_cached_verified_identity(
            access_token,
            {"auth_user_id": auth_user_id, "email": normalized_email},
        )
        return {
            "token": access_token,
            "user": _sanitize_profile(profile),
        }

    def logout(self, token: str | None) -> bool:
        bind_request_access_token(None)
        if not token:
            return False
        self._invalidate_token_cache(token.strip())
        if self._is_online_mode:
            sign_out_fn = getattr(self._repo, "auth_sign_out", None)
            return bool(sign_out_fn(token)) if callable(sign_out_fn) else False
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def request_password_recovery(
        self, email: str, redirect_to: str | None = None
    ) -> dict[str, Any]:
        normalized_email = _require_text(email, "email", "Email").lower()
        if (
            not normalized_email
            or len(normalized_email) > EMAIL_MAX_LENGTH
            or not EMAIL_PATTERN.match(normalized_email)
        ):
            raise DomainValidationError("Alamat email tidak valid.", {"field": "email"})

        safe_redirect = _validate_recovery_redirect_url(redirect_to)
        if self._is_online_mode:
            recover_fn = getattr(self._repo, "auth_request_password_recovery", None)
            if not callable(recover_fn):
                raise DomainValidationError(
                    "Repository Supabase tidak mendukung operasi pemulihan password."
                )
            return recover_fn(normalized_email, redirect_to=safe_redirect)

        return {
            "recovery_requested": True,
            "mode": "mock",
            "redirect_to": safe_redirect,
        }

    def complete_password_recovery(
        self,
        *,
        new_password: Any,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_hash: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(new_password, str):
            raise DomainValidationError(
                "Password baru harus berupa teks.", {"field": "new_password"}
            )
        if not new_password.strip() or len(new_password) < PASSWORD_MIN_LENGTH:
            raise DomainValidationError(
                f"Password baru minimal terdiri dari {PASSWORD_MIN_LENGTH} karakter.",
                {"field": "new_password"},
            )
        if len(new_password) > PASSWORD_MAX_LENGTH:
            raise DomainValidationError(
                f"Password baru maksimal {PASSWORD_MAX_LENGTH} karakter.",
                {"field": "new_password"},
            )

        clean_access = access_token.strip() if isinstance(access_token, str) else ""
        clean_refresh = refresh_token.strip() if isinstance(refresh_token, str) else ""
        clean_hash = token_hash.strip() if isinstance(token_hash, str) else ""

        if self._is_online_mode:
            update_fn = getattr(self._repo, "auth_update_password", None)
            if not callable(update_fn):
                raise DomainValidationError(
                    "Repository Supabase tidak mendukung pembaruan password Auth."
                )

            if clean_access and not clean_hash:
                get_user_fn = getattr(self._repo, "auth_get_user", None)
                if not callable(get_user_fn):
                    raise DomainUnauthorizedError("Layanan verifikasi token tidak tersedia.")
                verified = get_user_fn(clean_access)
                if not verified or not verified.get("auth_user_id"):
                    raise DomainUnauthorizedError(
                        "Tautan atau token pemulihan password tidak valid atau sudah kedaluwarsa."
                    )
                with use_access_token(clean_access):
                    profile = self._find_profile_by_auth_user_id(str(verified["auth_user_id"]))
                if not profile:
                    raise DomainUnauthorizedError(
                        PROFILE_NOT_PROVISIONED_MESSAGE,
                        {"reason": "profile_not_provisioned"},
                    )
                if not profile.get("is_active", True):
                    raise DomainForbiddenError("Akun pengguna tidak aktif.")

            try:
                result = update_fn(
                    new_password=new_password,
                    access_token=clean_access or None,
                    refresh_token=clean_refresh or None,
                    token_hash=clean_hash or None,
                )
            finally:
                if clean_access:
                    self._invalidate_token_cache(clean_access)
                bind_request_access_token(None)

            return {
                "password_updated": bool(result.get("password_updated", True)),
                "auth_user_id": str(result.get("auth_user_id") or ""),
            }

        user_id = self._sessions.get(clean_access) if clean_access else None
        if not user_id:
            raise DomainUnauthorizedError(
                "Token pemulihan password tidak valid atau tidak ditemukan."
            )
        profile = self._repo.get_profile_by_id(user_id)
        if not profile or not profile.get("is_active", True):
            raise DomainUnauthorizedError(
                "Akun pengguna untuk pemulihan password tidak aktif atau tidak ditemukan."
            )
        self._repo.update_profile(
            profile["id"], {"password_hash": generate_password_hash(new_password)}
        )
        return {
            "password_updated": True,
            "auth_user_id": str(profile.get("auth_user_id") or profile["id"]),
        }

    def get_user_by_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            bind_request_access_token(None)
            return None
        clean_token = token.strip()
        if not clean_token:
            bind_request_access_token(None)
            return None

        if self._is_online_mode:
            if clean_token.startswith("tok_"):
                bind_request_access_token(None)
                return None
            verified = self._get_cached_verified_identity(clean_token)
            if verified is None:
                get_user_fn = getattr(self._repo, "auth_get_user", None)
                if not callable(get_user_fn):
                    bind_request_access_token(None)
                    return None
                verified = get_user_fn(clean_token)
                if not verified or not verified.get("auth_user_id"):
                    bind_request_access_token(None)
                    return None
                self._set_cached_verified_identity(clean_token, verified)

            with use_access_token(clean_token):
                profile = self._find_profile_by_auth_user_id(str(verified["auth_user_id"]))
            if not profile or not profile.get("is_active", True):
                bind_request_access_token(None)
                return None
            bind_request_access_token(clean_token)
            return _sanitize_profile(profile)

        user_id = self._sessions.get(clean_token)
        if not user_id:
            return None
        profile = self._repo.get_profile_by_id(user_id)
        if not profile or not profile.get("is_active", True):
            return None
        return _sanitize_profile(profile)

    def get_user_by_mock_header(
        self, mock_user_id: str | None = None, mock_role: str | None = None
    ) -> dict[str, Any] | None:
        """Resolve a demo user in `APP_MODE=mock` by ID or role for parallel testing."""
        if self._is_online_mode:
            return None
        if mock_user_id:
            profile = self._repo.get_profile_by_id(mock_user_id)
            if profile and profile.get("is_active", True):
                return _sanitize_profile(profile)
        if mock_role:
            role_clean = mock_role.strip().lower()
            for p in self._repo.list_profiles():
                if p.get("role") == role_clean and p.get("is_active", True):
                    return _sanitize_profile(p)
        return None

    def get_profile(self, user_id: str) -> dict[str, Any]:
        profile = self._repo.get_profile_by_id(user_id)
        if not profile:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": user_id})
        return _sanitize_profile(profile)

    def update_profile(
        self,
        actor: dict[str, Any] | None,
        target_user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        active_actor = require_authenticated(actor)
        is_super_admin = active_actor.get("role") == ROLE_SUPER_ADMIN
        if active_actor["id"] != target_user_id and not is_super_admin:
            raise DomainForbiddenError(
                "Anda hanya diizinkan memperbarui profil milik sendiri.",
                details={"actor_id": active_actor["id"], "target_user_id": target_user_id},
            )

        existing = self._repo.get_profile_by_id(target_user_id)
        if not existing:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": target_user_id})

        raw_role = payload.get("role")
        if raw_role is not None:
            requested_role = _require_text(raw_role, "role", "Role").lower()
            if requested_role != existing.get("role") and not is_super_admin:
                raise DomainForbiddenError(
                    "Pengguna biasa tidak diizinkan mengubah role miliknya sendiri.",
                    details={"requested_role": raw_role},
                )

        updates: dict[str, Any] = {}
        if "full_name" in payload and payload["full_name"] is not None:
            updates["full_name"] = _validate_full_name(payload["full_name"])
        if "phone" in payload:
            raw_phone = payload["phone"]
            if raw_phone is None or (isinstance(raw_phone, str) and not raw_phone.strip()):
                updates["phone"] = None
            else:
                phone = _require_text(raw_phone, "phone", "Nomor telepon")
                if len(phone) > PHONE_MAX_LENGTH:
                    raise DomainValidationError(
                        f"Nomor telepon maksimal {PHONE_MAX_LENGTH} karakter.", {"field": "phone"}
                    )
                updates["phone"] = phone
        if "avatar_url" in payload:
            raw_avatar = payload["avatar_url"]
            if raw_avatar is None or (isinstance(raw_avatar, str) and not raw_avatar.strip()):
                updates["avatar_url"] = None
            else:
                updates["avatar_url"] = _require_text(raw_avatar, "avatar_url", "URL avatar")

        updated = self._repo.update_profile(target_user_id, updates) if updates else existing
        assert updated is not None
        self._invalidate_token_cache()
        self._repo.log_activity(
            actor_id=active_actor["id"],
            tournament_id=None,
            entity_type="profile",
            entity_id=target_user_id,
            action="PROFILE_UPDATED",
            details={"updated_fields": list(updates.keys())},
        )
        return _sanitize_profile(updated)

    def list_users(self, actor: dict[str, Any] | None) -> list[dict[str, Any]]:
        require_permission(actor, "user:assign_role")
        profiles = self._repo.list_profiles()
        results: list[dict[str, Any]] = []
        for p in profiles:
            item = _sanitize_profile(p)
            item["is_auth_linked"] = bool(p.get("auth_user_id"))
            results.append(item)
        results.sort(key=lambda u: (str(u.get("full_name") or "").lower(), str(u.get("email") or "")))
        return results

    def assign_role(
        self,
        actor: dict[str, Any] | None,
        target_user_id: str,
        new_role: str,
    ) -> dict[str, Any]:
        active_actor = require_permission(actor, "user:assign_role")
        normalized_role = _require_text(new_role, "role", "Role").lower()
        if normalized_role not in ALL_ROLES:
            raise DomainValidationError(f"Role '{normalized_role}' tidak dikenali.", {"field": "role"})

        existing = self._repo.get_profile_by_id(target_user_id)
        if not existing:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": target_user_id})

        updated = self._repo.assign_user_role(target_user_id, normalized_role)
        if not updated:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": target_user_id})
        self._invalidate_token_cache()
        self._repo.log_activity(
            actor_id=active_actor["id"],
            tournament_id=None,
            entity_type="profile",
            entity_id=target_user_id,
            action="USER_ROLE_ASSIGNED",
            details={"old_role": existing.get("role"), "new_role": normalized_role},
        )
        out = _sanitize_profile(updated)
        out["is_auth_linked"] = bool(updated.get("auth_user_id"))
        return out
