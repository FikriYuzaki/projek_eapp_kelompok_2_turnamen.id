"""Role-Based Access Control (RBAC) permission definitions and guards.

Owner: Habil (Database & Authentication Developer)
Enforces the 5-role permission matrix defined in `docs/contracts/role-permissions.md`.
"""

from __future__ import annotations

from typing import Any, Iterable

from backend.contracts.dtos import (
    ALL_ROLES,
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_PLAYER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
)
from backend.core.exceptions import DomainForbiddenError, DomainUnauthorizedError

PERMISSION_MATRIX: dict[str, tuple[str, ...]] = {
    # Tournaments
    "tournament:create": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER),
    "tournament:update": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER),
    "tournament:delete": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER),
    # Teams
    "team:create": (ROLE_SUPER_ADMIN, ROLE_TEAM_CAPTAIN),
    "team:update": (ROLE_SUPER_ADMIN, ROLE_TEAM_CAPTAIN),
    "team:add_member": (ROLE_SUPER_ADMIN, ROLE_TEAM_CAPTAIN),
    # Registrations
    "registration:create": (ROLE_SUPER_ADMIN, ROLE_TEAM_CAPTAIN),
    "registration:verify": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE),
    # Matches & Bracket
    "bracket:generate": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE),
    "match:submit_result": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE),
    # Announcements
    "announcement:create": (ROLE_SUPER_ADMIN, ROLE_ORGANIZER, ROLE_COMMITTEE),
    # User & Role Management
    "user:assign_role": (ROLE_SUPER_ADMIN,),
}


def has_permission(role: str, action: str) -> bool:
    """Return True if the given `role` is permitted to perform `action`."""
    if role not in ALL_ROLES:
        return False
    allowed = PERMISSION_MATRIX.get(action)
    if allowed is None:
        return False
    return role in allowed


def require_authenticated(user: dict[str, Any] | None) -> dict[str, Any]:
    """Raise `DomainUnauthorizedError` if `user` is None or inactive."""
    if not user:
        raise DomainUnauthorizedError(
            "Sesi autentikasi diperlukan. Silakan login terlebih dahulu."
        )
    if not user.get("is_active", True):
        raise DomainForbiddenError("Akun pengguna sedang dinonaktifkan.")
    return user


def require_permission(user: dict[str, Any] | None, action: str) -> dict[str, Any]:
    """Verify that `user` is authenticated and their role is allowed for `action`."""
    active_user = require_authenticated(user)
    role = str(active_user.get("role", ROLE_PLAYER))
    if not has_permission(role, action):
        allowed_roles = ", ".join(PERMISSION_MATRIX.get(action, ()))
        raise DomainForbiddenError(
            f"Akses ditolak: Role '{role}' tidak memiliki izin untuk operasi '{action}'.",
            details={"required_roles": allowed_roles, "current_role": role, "action": action},
        )
    return active_user


def require_any_role(user: dict[str, Any] | None, allowed_roles: Iterable[str]) -> dict[str, Any]:
    """Verify that `user` holds one of the specified `allowed_roles`."""
    active_user = require_authenticated(user)
    role = str(active_user.get("role", ""))
    allowed_set = tuple(allowed_roles)
    if role not in allowed_set:
        raise DomainForbiddenError(
            f"Akses ditolak: Role '{role}' tidak diizinkan.",
            details={"required_roles": list(allowed_set), "current_role": role},
        )
    return active_user
