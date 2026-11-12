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

import secrets
from typing import Any
from werkzeug.security import check_password_hash, generate_password_hash

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


def _sanitize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Strip internal sensitive fields before returning profile data to callers."""
    return {
        k: v
        for k, v in profile.items()
        if k not in ("password_hash", "access_token")
    }


class AuthService:
    """Application service handling registration, login, session lookup, and role security."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository
        self._sessions: dict[str, str] = {}

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
        email = str(payload.get("email") or "").strip().lower()
        username = str(payload.get("username") or "").strip()
        full_name = str(payload.get("full_name") or "").strip()
        password = str(payload.get("password") or "")
        requested_role = str(payload.get("role") or ROLE_PLAYER).strip().lower()
        phone = str(payload["phone"]).strip() if payload.get("phone") else None

        if not email or "@" not in email:
            raise DomainValidationError("Alamat email tidak valid.", {"field": "email"})
        if len(username) < 3:
            raise DomainValidationError("Username minimal terdiri dari 3 karakter.", {"field": "username"})
        if len(full_name) < 2:
            raise DomainValidationError("Nama lengkap wajib diisi.", {"field": "full_name"})
        if len(password) < 6:
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
            profile = self._find_profile_by_auth_user_id(auth_user_id)
            if not profile:
                existing_by_email = self._repo.get_profile_by_email(email)
                if existing_by_email and not existing_by_email.get("auth_user_id"):
                    profile = self._repo.update_profile(
                        existing_by_email["id"],
                        {
                            "auth_user_id": auth_user_id,
                            "full_name": full_name,
                            "phone": phone,
                        },
                    )
                else:
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
        normalized_email = str(email or "").strip().lower()
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
                by_email = self._repo.get_profile_by_email(normalized_email)
                if by_email:
                    if by_email.get("auth_user_id") and by_email.get("auth_user_id") != auth_user_id:
                        raise DomainUnauthorizedError("Identitas akun tidak cocok dengan profil terdaftar.")
                    profile = (
                        self._repo.update_profile(
                            by_email["id"],
                            {"auth_user_id": auth_user_id},
                        )
                        or by_email
                    )

        if not profile:
            raise DomainUnauthorizedError("Profil pengguna tidak ditemukan pada sistem.")

        if not profile.get("is_active", True):
            raise DomainForbiddenError("Akun pengguna tidak aktif.")

        bind_request_access_token(access_token)
        return {
            "token": access_token,
            "user": _sanitize_profile(profile),
        }

    def logout(self, token: str | None) -> bool:
        bind_request_access_token(None)
        if not token:
            return False
        if self._is_online_mode:
            sign_out_fn = getattr(self._repo, "auth_sign_out", None)
            return bool(sign_out_fn(token)) if callable(sign_out_fn) else False
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

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
            get_user_fn = getattr(self._repo, "auth_get_user", None)
            if not callable(get_user_fn):
                bind_request_access_token(None)
                return None
            verified = get_user_fn(clean_token)
            if not verified or not verified.get("auth_user_id"):
                bind_request_access_token(None)
                return None
            with use_access_token(clean_token):
                profile = self._find_profile_by_auth_user_id(str(verified["auth_user_id"]))
                if not profile and verified.get("email"):
                    candidate = self._repo.get_profile_by_email(str(verified["email"]))
                    if candidate and candidate.get("auth_user_id") in (None, str(verified["auth_user_id"])):
                        profile = candidate
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

        if "role" in payload and payload["role"] != existing.get("role") and not is_super_admin:
            raise DomainForbiddenError(
                "Pengguna biasa tidak diizinkan mengubah role miliknya sendiri.",
                details={"requested_role": payload["role"]},
            )

        updates: dict[str, Any] = {}
        if "full_name" in payload and payload["full_name"] is not None:
            full_name = str(payload["full_name"]).strip()
            if len(full_name) < 2:
                raise DomainValidationError("Nama lengkap minimal terdiri dari 2 karakter.", {"field": "full_name"})
            updates["full_name"] = full_name
        if "phone" in payload:
            updates["phone"] = str(payload["phone"]).strip() if payload["phone"] else None
        if "avatar_url" in payload:
            updates["avatar_url"] = str(payload["avatar_url"]).strip() if payload["avatar_url"] else None

        updated = self._repo.update_profile(target_user_id, updates) if updates else existing
        assert updated is not None
        self._repo.log_activity(
            actor_id=active_actor["id"],
            tournament_id=None,
            entity_type="profile",
            entity_id=target_user_id,
            action="PROFILE_UPDATED",
            details={"updated_fields": list(updates.keys())},
        )
        return _sanitize_profile(updated)

    def assign_role(
        self,
        actor: dict[str, Any] | None,
        target_user_id: str,
        new_role: str,
    ) -> dict[str, Any]:
        active_actor = require_permission(actor, "user:assign_role")
        normalized_role = str(new_role or "").strip().lower()
        if normalized_role not in ALL_ROLES:
            raise DomainValidationError(f"Role '{normalized_role}' tidak dikenali.", {"field": "role"})

        existing = self._repo.get_profile_by_id(target_user_id)
        if not existing:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": target_user_id})

        updated = self._repo.update_profile(target_user_id, {"role": normalized_role})
        assert updated is not None
        self._repo.log_activity(
            actor_id=active_actor["id"],
            tournament_id=None,
            entity_type="profile",
            entity_id=target_user_id,
            action="USER_ROLE_ASSIGNED",
            details={"old_role": existing.get("role"), "new_role": normalized_role},
        )
        return _sanitize_profile(updated)
