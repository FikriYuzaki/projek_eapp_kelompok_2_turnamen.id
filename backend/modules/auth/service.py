"""Authentication and session service for Turnamen.in.

Owner: Habil (Database & Authentication Developer)
Security Rules:
- Self-registration can only assign `player` or `team_captain` roles.
- Passwords are hashed using Werkzeug PBKDF2/Scrypt and never returned in responses.
"""

from __future__ import annotations

import secrets
from typing import Any
from werkzeug.security import check_password_hash, generate_password_hash

from backend.contracts.dtos import (
    ALL_ROLES,
    ROLE_PLAYER,
    SELF_REGISTRABLE_ROLES,
)
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainUnauthorizedError,
    DomainValidationError,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol


def _sanitize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Strip internal password hash before returning profile data to callers."""
    return {k: v for k, v in profile.items() if k != "password_hash"}


class AuthService:
    """Application service handling registration, login, session lookup, and role security."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository
        self._sessions: dict[str, str] = {}

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = str(payload.get("email") or "").strip().lower()
        username = str(payload.get("username") or "").strip()
        full_name = str(payload.get("full_name") or "").strip()
        password = str(payload.get("password") or "")
        requested_role = str(payload.get("role") or ROLE_PLAYER).strip().lower()

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
                "phone": payload.get("phone"),
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

    def login(self, email: str, password: str) -> dict[str, Any]:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email or not password:
            raise DomainValidationError("Email dan password wajib diisi.")

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

    def logout(self, token: str | None) -> bool:
        if token and token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def get_user_by_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        user_id = self._sessions.get(token)
        if not user_id:
            return None
        profile = self._repo.get_profile_by_id(user_id)
        return _sanitize_profile(profile) if profile else None

    def get_user_by_mock_header(
        self, mock_user_id: str | None = None, mock_role: str | None = None
    ) -> dict[str, Any] | None:
        """Resolve a demo user in `APP_MODE=mock` by ID or role for parallel testing."""
        if mock_user_id:
            profile = self._repo.get_profile_by_id(mock_user_id)
            if profile:
                return _sanitize_profile(profile)
        if mock_role:
            role_clean = mock_role.strip().lower()
            for p in self._repo.list_profiles():
                if p.get("role") == role_clean:
                    return _sanitize_profile(p)
        return None

    def get_profile(self, user_id: str) -> dict[str, Any]:
        profile = self._repo.get_profile_by_id(user_id)
        if not profile:
            raise DomainNotFoundError("Profil pengguna tidak ditemukan.", {"user_id": user_id})
        return _sanitize_profile(profile)
