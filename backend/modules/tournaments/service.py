"""Service untuk manajemen turnamen dan pendaftaran tim."""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.contracts.dtos import (
    REGISTRATION_STATUSES,
    ROLE_COMMITTEE,
    ROLE_ORGANIZER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_CAPTAIN,
    TOURNAMENT_STATUSES,
)
from backend.core.exceptions import (
    DomainConflictError,
    DomainForbiddenError,
    DomainNotFoundError,
    DomainValidationError,
)
from backend.modules.auth.permissions import (
    is_tournament_manager,
    require_any_role,
    require_authenticated,
    require_permission,
)
from backend.modules.matches.bracket_engine import parse_best_of, parse_strict_int
from backend.modules.tournaments.artwork_validator import (
    generate_unique_artwork_path,
    validate_and_inspect_artwork_upload,
)
from backend.repositories.interfaces.repository_protocol import DataStoreRepositoryProtocol

TITLE_MIN_LENGTH = 4
TITLE_MAX_LENGTH = 180
VENUE_MAX_LENGTH = 180
MIN_TEAMS = 2
MAX_TEAMS = 128

# Allowed forward moves; completed and cancelled are terminal so history cannot be rewritten.
ALLOWED_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("open_registration", "registration_closed", "cancelled"),
    "open_registration": ("draft", "registration_closed", "ongoing", "cancelled"),
    "registration_closed": ("open_registration", "ongoing", "cancelled"),
    "ongoing": ("completed", "cancelled"),
    "completed": (),
    "cancelled": (),
}
REGISTRATION_LOCKED_STATUSES = ("ongoing", "completed", "cancelled")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"tournament-{uuid.uuid4().hex[:8]}"


def _require_optional_text(raw: Any, field: str, default: str = "") -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise DomainValidationError(f"Field {field} harus berupa teks.", {"field": field})
    return raw.strip()


def _parse_bool(raw: Any, field: str) -> bool:
    if not isinstance(raw, bool):
        raise DomainValidationError(
            f"Field {field} harus berupa boolean (true/false).", {"field": field}
        )
    return raw


def _validate_venue(raw: Any, default: str | None = None) -> str:
    if raw is None:
        if default is not None:
            return default
        raise DomainValidationError("Field venue tidak boleh kosong.", {"field": "venue"})
    if not isinstance(raw, str):
        raise DomainValidationError("Field venue harus berupa teks.", {"field": "venue"})
    venue = raw.strip()
    if not venue or len(venue) > VENUE_MAX_LENGTH:
        raise DomainValidationError(
            f"Venue turnamen harus terdiri dari 1 hingga {VENUE_MAX_LENGTH} karakter.",
            {"field": "venue"},
        )
    return venue


def _validate_title(raw: Any) -> str:
    if not isinstance(raw, str):
        raise DomainValidationError("Judul turnamen harus berupa teks.", {"field": "title"})
    title = raw.strip()
    if len(title) < TITLE_MIN_LENGTH or len(title) > TITLE_MAX_LENGTH:
        raise DomainValidationError(
            f"Judul turnamen harus terdiri dari {TITLE_MIN_LENGTH} hingga "
            f"{TITLE_MAX_LENGTH} karakter.",
            {"field": "title"},
        )
    return title


def _parse_max_teams(raw: Any) -> int:
    max_teams = parse_strict_int(raw, "max_teams")
    if max_teams < MIN_TEAMS or max_teams > MAX_TEAMS:
        raise DomainValidationError(
            f"Kuota tim (max_teams) harus berada di antara {MIN_TEAMS} hingga {MAX_TEAMS}.",
            {"field": "max_teams", "max_teams": max_teams},
        )
    return max_teams


def _parse_money(raw: Any, field: str) -> float:
    if isinstance(raw, bool):
        raise DomainValidationError(f"Field {field} harus berupa angka.", {"field": field})
    try:
        amount = float(raw)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(f"Field {field} harus berupa angka.", {"field": field}) from exc
    if not math.isfinite(amount) or amount < 0:
        raise DomainValidationError(
            f"Field {field} harus berupa angka yang tidak negatif.", {"field": field}
        )
    return amount


def _parse_datetime(raw: Any, field: str) -> datetime:
    text = str(raw or "").strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DomainValidationError(
            f"Field {field} harus berupa tanggal ISO-8601 yang valid.", {"field": field}
        ) from exc
    # Date-only and naive values are compared as UTC so they can be ordered against aware ones.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _validate_date_range(start_raw: Any, end_raw: Any) -> None:
    if end_raw in (None, ""):
        return
    if _parse_datetime(end_raw, "end_date") < _parse_datetime(start_raw, "start_date"):
        raise DomainValidationError(
            "Tanggal selesai (end_date) tidak boleh lebih awal dari tanggal mulai (start_date).",
            {"field": "end_date"},
        )


STAFF_ROLES: tuple[str, ...] = ("head_committee", "referee", "verifier", "announcer")


class TournamentService:
    """Pengelolaan turnamen dan registrasi peserta."""

    def __init__(self, repository: DataStoreRepositoryProtocol) -> None:
        self._repo = repository

    def list_games(
        self, include_inactive: bool = False, actor: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        allow_inactive = bool(
            include_inactive
            and actor
            and actor.get("is_active", True)
            and str(actor.get("role") or "").strip().lower() == ROLE_SUPER_ADMIN
        )
        if allow_inactive:
            return self._repo.list_games(include_inactive=True)
        return self._repo.list_games()

    def get_game(self, game_id: str) -> dict[str, Any]:
        game = self._repo.get_game_by_id(game_id)
        if not game:
            raise DomainNotFoundError("Data game tidak ditemukan.", {"game_id": game_id})
        return game

    def create_game(self, actor: dict[str, Any] | None, payload: dict[str, Any]) -> dict[str, Any]:
        user = require_permission(actor, "game:manage")
        name = _require_optional_text(payload.get("name"), "name")
        if len(name) < 2 or len(name) > 120:
            raise DomainValidationError(
                "Nama cabang game harus terdiri dari 2 hingga 120 karakter.", {"field": "name"}
            )
        genre = _require_optional_text(payload.get("genre"), "genre")
        if len(genre) < 2 or len(genre) > 64:
            raise DomainValidationError(
                "Genre game harus terdiri dari 2 hingga 64 karakter.", {"field": "genre"}
            )
        platform = _require_optional_text(payload.get("platform"), "platform", default="PC / Mobile") or "PC / Mobile"
        if len(platform) > 64:
            raise DomainValidationError(
                "Nama platform maksimal 64 karakter.", {"field": "platform"}
            )

        raw_team_size = payload.get("team_size")
        team_size = 5 if raw_team_size is None else parse_strict_int(raw_team_size, "team_size")
        if team_size < 1 or team_size > 20:
            raise DomainValidationError(
                "Ukuran tim (team_size) harus berada di antara 1 hingga 20.", {"field": "team_size"}
            )

        raw_subs = payload.get("max_substitutes")
        max_substitutes = 2 if raw_subs is None else parse_strict_int(raw_subs, "max_substitutes")
        if max_substitutes < 0 or max_substitutes > 10:
            raise DomainValidationError(
                "Maksimal cadangan (max_substitutes) harus berada di antara 0 hingga 10.",
                {"field": "max_substitutes"},
            )

        allow_draw = _parse_bool(payload.get("allow_draw", False), "allow_draw")
        raw_bo = payload.get("default_best_of")
        default_best_of = parse_best_of(3 if raw_bo is None else raw_bo)
        is_active = _parse_bool(payload.get("is_active", True), "is_active")

        raw_slug = _require_optional_text(payload.get("slug"), "slug")
        slug = _slugify(raw_slug or name)[:64]
        if self._repo.get_game_by_id(slug):
            slug = f"{slug[:57]}-{uuid.uuid4().hex[:6]}"

        created = self._repo.create_game(
            {
                "slug": slug,
                "name": name,
                "genre": genre,
                "platform": platform,
                "team_size": team_size,
                "max_substitutes": max_substitutes,
                "allow_draw": allow_draw,
                "default_best_of": default_best_of,
                "is_active": is_active,
            }
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=None,
            entity_type="game",
            entity_id=created["id"],
            action="GAME_CREATED",
            details={"name": name, "slug": slug},
        )
        return created

    def update_game(
        self, actor: dict[str, Any] | None, game_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "game:manage")
        existing = self.get_game(game_id)
        updates: dict[str, Any] = {}

        if "name" in payload and payload["name"] is not None:
            name = _require_optional_text(payload["name"], "name")
            if len(name) < 2 or len(name) > 120:
                raise DomainValidationError(
                    "Nama cabang game harus terdiri dari 2 hingga 120 karakter.", {"field": "name"}
                )
            updates["name"] = name
        if "genre" in payload and payload["genre"] is not None:
            genre = _require_optional_text(payload["genre"], "genre")
            if len(genre) < 2 or len(genre) > 64:
                raise DomainValidationError(
                    "Genre game harus terdiri dari 2 hingga 64 karakter.", {"field": "genre"}
                )
            updates["genre"] = genre
        if "platform" in payload and payload["platform"] is not None:
            platform = _require_optional_text(payload["platform"], "platform")
            if not platform or len(platform) > 64:
                raise DomainValidationError(
                    "Platform game harus 1 hingga 64 karakter.", {"field": "platform"}
                )
            updates["platform"] = platform
        if "team_size" in payload and payload["team_size"] is not None:
            team_size = parse_strict_int(payload["team_size"], "team_size")
            if team_size < 1 or team_size > 20:
                raise DomainValidationError(
                    "Ukuran tim (team_size) harus berada di antara 1 hingga 20.",
                    {"field": "team_size"},
                )
            updates["team_size"] = team_size
        if "max_substitutes" in payload and payload["max_substitutes"] is not None:
            subs = parse_strict_int(payload["max_substitutes"], "max_substitutes")
            if subs < 0 or subs > 10:
                raise DomainValidationError(
                    "Maksimal cadangan (max_substitutes) harus berada di antara 0 hingga 10.",
                    {"field": "max_substitutes"},
                )
            updates["max_substitutes"] = subs
        if "allow_draw" in payload and payload["allow_draw"] is not None:
            updates["allow_draw"] = _parse_bool(payload["allow_draw"], "allow_draw")
        if "default_best_of" in payload and payload["default_best_of"] is not None:
            updates["default_best_of"] = parse_best_of(payload["default_best_of"])
        if "is_active" in payload and payload["is_active"] is not None:
            updates["is_active"] = _parse_bool(payload["is_active"], "is_active")

        if not updates:
            return existing
        updated = self._repo.update_game(existing["id"], updates)
        if not updated:
            raise DomainNotFoundError("Data game tidak ditemukan.", {"game_id": game_id})
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=None,
            entity_type="game",
            entity_id=existing["id"],
            action="GAME_UPDATED",
            details=updates,
        )
        return updated

    def upload_game_artwork(
        self,
        actor: dict[str, Any] | None,
        game_id: str,
        *,
        raw_bytes: bytes,
        filename: str = "",
        declared_content_type: str = "",
    ) -> dict[str, Any]:
        """Validate and replace custom game poster using upload -> metadata -> old cleanup ordering."""
        user = require_permission(actor, "game:manage")
        existing = self.get_game(game_id)
        inspected = validate_and_inspect_artwork_upload(
            raw_bytes,
            filename=filename,
            declared_content_type=declared_content_type,
        )
        previous_override = self._repo.get_game_artwork_override(existing["id"])
        new_storage_path = generate_unique_artwork_path(existing.get("slug") or existing["id"], inspected.extension)

        # Upload first so existing metadata never points to a missing object.
        self._repo.upload_game_artwork_object(
            new_storage_path,
            inspected.raw_bytes,
            inspected.mime_type,
        )

        try:
            self._repo.upsert_game_artwork_override(
                existing["id"],
                {
                    "storage_path": new_storage_path,
                    "mime_type": inspected.mime_type,
                    "file_size_bytes": inspected.file_size_bytes,
                    "width": inspected.width,
                    "height": inspected.height,
                    "uploaded_by": user["id"],
                },
            )
        except Exception:
            # Remove the newly uploaded orphan object when metadata write fails.
            self._repo.delete_game_artwork_object(new_storage_path)
            raise

        old_path = str((previous_override or {}).get("storage_path") or "").strip()
        if old_path and old_path != new_storage_path:
            self._repo.delete_game_artwork_object(old_path)

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=None,
            entity_type="game",
            entity_id=existing["id"],
            action="GAME_ARTWORK_UPDATED",
            details={
                "storage_path": new_storage_path,
                "mime_type": inspected.mime_type,
                "width": inspected.width,
                "height": inspected.height,
            },
        )
        updated = self.get_game(existing["id"])
        if inspected.aspect_ratio_warning:
            updated["aspect_ratio_warning"] = inspected.aspect_ratio_warning
        return updated

    def restore_game_artwork(self, actor: dict[str, Any] | None, game_id: str) -> dict[str, Any]:
        """Remove custom game artwork override first, then clean up unused storage object."""
        user = require_permission(actor, "game:manage")
        existing = self.get_game(game_id)
        previous_override = self._repo.get_game_artwork_override(existing["id"])

        deleted_override = self._repo.delete_game_artwork_override(existing["id"])
        old_path = str((deleted_override or previous_override or {}).get("storage_path") or "").strip()
        if old_path:
            self._repo.delete_game_artwork_object(old_path)

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=None,
            entity_type="game",
            entity_id=existing["id"],
            action="GAME_ARTWORK_RESTORED",
            details={"removed_storage_path": old_path or None},
        )
        return self.get_game(existing["id"])

    def get_mock_artwork_asset(self, storage_path: str) -> tuple[str, bytes] | None:
        """Retrieve uploaded mock poster bytes for local dev/test HTTP asset delivery."""
        getter = getattr(self._repo, "get_mock_artwork_blob", None)
        return getter(storage_path) if callable(getter) else None

    def list_committee_candidates(self, actor: dict[str, Any] | None) -> list[dict[str, Any]]:
        require_any_role(actor, (ROLE_SUPER_ADMIN, ROLE_ORGANIZER))
        return self._repo.list_committee_candidates()

    def list_tournament_staff(
        self, actor: dict[str, Any] | None, tournament_id: str
    ) -> list[dict[str, Any]]:
        user = require_authenticated(actor)
        tournament = self.get_tournament(tournament_id)
        if not is_tournament_manager(self._repo, user, tournament):
            raise DomainForbiddenError(
                "Hanya Super Admin, Organizer pemilik, atau Panitia ditugaskan yang dapat melihat daftar staf."
            )
        return self._repo.list_tournament_staff(tournament["id"])

    def add_tournament_staff(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_any_role(actor, (ROLE_SUPER_ADMIN, ROLE_ORGANIZER))
        tournament = self.get_tournament(tournament_id)
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat menugaskan panitia pada turnamen miliknya sendiri."
            )
        target_user_id = _require_optional_text(payload.get("user_id"), "user_id")
        if not target_user_id:
            raise DomainValidationError("user_id panitia wajib dipilih.", {"field": "user_id"})
        staff_role = _require_optional_text(
            payload.get("staff_role"), "staff_role", default="referee"
        ).lower()
        if staff_role not in STAFF_ROLES:
            raise DomainValidationError(
                f"Peran staf '{staff_role}' tidak valid.",
                {"field": "staff_role", "valid_roles": list(STAFF_ROLES)},
            )
        created = self._repo.add_tournament_staff(tournament["id"], target_user_id, staff_role)
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="tournament_staff",
            entity_id=created.get("id"),
            action="TOURNAMENT_STAFF_ASSIGNED",
            details={"user_id": target_user_id, "staff_role": staff_role},
        )
        return created

    def remove_tournament_staff(
        self, actor: dict[str, Any] | None, tournament_id: str, user_id: str
    ) -> dict[str, Any]:
        user = require_any_role(actor, (ROLE_SUPER_ADMIN, ROLE_ORGANIZER))
        tournament = self.get_tournament(tournament_id)
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat mencabut panitia pada turnamen miliknya sendiri."
            )
        removed = self._repo.remove_tournament_staff(tournament["id"], user_id)
        if not removed:
            raise DomainNotFoundError(
                "Penugasan panitia pada turnamen ini tidak ditemukan.",
                {"tournament_id": tournament["id"], "user_id": user_id},
            )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="tournament_staff",
            entity_id=None,
            action="TOURNAMENT_STAFF_REMOVED",
            details={"user_id": user_id},
        )
        return {"removed": True, "tournament_id": tournament["id"], "user_id": user_id}

    @staticmethod
    def _is_committee_actor(actor: dict[str, Any] | None) -> bool:
        return bool(
            actor
            and actor.get("is_active", True)
            and str(actor.get("role") or "").strip().lower() == ROLE_COMMITTEE
        )

    def list_tournaments(
        self,
        status: str | None = None,
        game_id: str | None = None,
        actor: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if status and status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(
                f"Status filter '{status}' tidak valid.",
                {"valid_statuses": list(TOURNAMENT_STATUSES)},
            )
        items = self._repo.list_tournaments(status=status, game_id=game_id)
        if self._is_committee_actor(actor):
            assigned_ids = set(self._repo.list_assigned_tournament_ids(str(actor["id"])))  # type: ignore[index]
            for item in items:
                item["is_assigned_committee"] = item["id"] in assigned_ids
        return items

    def get_tournament(
        self, tournament_id: str, actor: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        tournament = self._repo.get_tournament_by_id(tournament_id)
        if not tournament:
            raise DomainNotFoundError(
                "Turnamen tidak ditemukan.", {"tournament_id": tournament_id}
            )
        if self._is_committee_actor(actor):
            tournament["is_assigned_committee"] = self._repo.is_staff_assigned(
                tournament["id"], str(actor["id"])  # type: ignore[index]
            )
        return tournament

    def create_tournament(
        self, actor: dict[str, Any] | None, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "tournament:create")
        title = _validate_title(payload.get("title"))
        game_id = str(payload.get("game_id") or "").strip()
        start_date = str(payload.get("start_date") or "").strip()

        if not game_id:
            raise DomainValidationError("Game wajib dipilih.", {"field": "game_id"})
        game = self._repo.get_game_by_id(game_id)
        if not game:
            raise DomainNotFoundError("Game tidak ditemukan.", {"game_id": game_id})
        if not start_date:
            raise DomainValidationError(
                "Tanggal mulai turnamen (start_date) wajib diisi.", {"field": "start_date"}
            )
        _parse_datetime(start_date, "start_date")
        end_date = payload.get("end_date")
        end_date = str(end_date).strip() if end_date not in (None, "") else None
        _validate_date_range(start_date, end_date)

        raw_max_teams = payload.get("max_teams")
        max_teams = _parse_max_teams(8 if raw_max_teams is None else raw_max_teams)

        raw_best_of = payload.get("best_of")
        best_of = parse_best_of(
            game.get("default_best_of", 3) if raw_best_of is None else raw_best_of
        )

        raw_fee = payload.get("registration_fee")
        raw_prize = payload.get("prize_pool")
        registration_fee = _parse_money(0.0 if raw_fee is None else raw_fee, "registration_fee")
        prize_pool = _parse_money(0.0 if raw_prize is None else raw_prize, "prize_pool")

        status_raw = payload.get("status")
        if status_raw is None:
            status = "open_registration"
        else:
            status = _require_optional_text(status_raw, "status") or "open_registration"
        if status not in TOURNAMENT_STATUSES:
            raise DomainValidationError(
                f"Status turnamen '{status}' tidak valid.", {"field": "status"}
            )

        raw_allow_draw = payload.get("allow_draw", False)
        allow_draw = _parse_bool(raw_allow_draw, "allow_draw")

        raw_slug = _require_optional_text(payload.get("slug"), "slug")
        base_slug = _slugify(raw_slug or title)
        slug = base_slug
        if self._repo.get_tournament_by_id(slug):
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        venue = _validate_venue(payload.get("venue"), default="Online")
        description = _require_optional_text(payload.get("description"), "description")
        rules = _require_optional_text(payload.get("rules"), "rules")

        created = self._repo.create_tournament(
            {
                "slug": slug,
                "title": title,
                "description": description,
                "game_id": game["id"],
                "organizer_id": user["id"],
                "format": "single_elimination",
                "status": status,
                "max_teams": max_teams,
                "best_of": best_of,
                "allow_draw": allow_draw,
                "registration_fee": registration_fee,
                "prize_pool": prize_pool,
                "rules": rules,
                "venue": venue,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=created["id"],
            entity_type="tournament",
            entity_id=created["id"],
            action="TOURNAMENT_CREATED",
            details={"title": title, "max_teams": max_teams, "best_of": best_of},
        )
        return created

    def update_tournament(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "tournament:update")
        tournament = self.get_tournament(tournament_id)

        if (
            user["role"] == ROLE_ORGANIZER
            and tournament["organizer_id"] != user["id"]
        ):
            raise DomainForbiddenError(
                "Organizer hanya dapat mengubah turnamen yang dikelolanya sendiri."
            )

        updates: dict[str, Any] = {}
        if "title" in payload and payload["title"] is not None:
            updates["title"] = _validate_title(payload["title"])
        for field in ("description", "rules"):
            if field in payload and payload[field] is not None:
                updates[field] = _require_optional_text(payload[field], field)
        if "venue" in payload and payload["venue"] is not None:
            updates["venue"] = _validate_venue(payload["venue"])
        if "allow_draw" in payload and payload["allow_draw"] is not None:
            updates["allow_draw"] = _parse_bool(payload["allow_draw"], "allow_draw")

        if "start_date" in payload and payload["start_date"] is not None:
            start_date = str(payload["start_date"]).strip()
            if not start_date:
                raise DomainValidationError(
                    "Tanggal mulai turnamen (start_date) wajib diisi.", {"field": "start_date"}
                )
            _parse_datetime(start_date, "start_date")
            updates["start_date"] = start_date
        if "end_date" in payload:
            raw_end = payload["end_date"]
            updates["end_date"] = str(raw_end).strip() if raw_end not in (None, "") else None
        if "start_date" in updates or "end_date" in updates:
            effective_start = updates.get("start_date", tournament.get("start_date"))
            effective_end = updates.get("end_date", tournament.get("end_date"))
            if effective_start:
                _validate_date_range(effective_start, effective_end)

        requested_status: str | None = None
        if "status" in payload and payload["status"] is not None:
            new_status = _require_optional_text(payload["status"], "status")
            if new_status not in TOURNAMENT_STATUSES:
                raise DomainValidationError(
                    f"Status turnamen '{new_status}' tidak valid.", {"field": "status"}
                )
            current_status = tournament["status"]
            allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, ())
            if new_status != current_status:
                if new_status not in allowed:
                    raise DomainConflictError(
                        f"Status turnamen tidak dapat diubah dari '{current_status}' ke '{new_status}'.",
                        {
                            "field": "status",
                            "current_status": current_status,
                            "requested_status": new_status,
                            "allowed_statuses": list(allowed),
                        },
                    )
                requested_status = new_status

        if "max_teams" in payload and payload["max_teams"] is not None:
            max_teams = _parse_max_teams(payload["max_teams"])
            approved_count = sum(
                1
                for r in self._repo.list_registrations_by_tournament(tournament["id"])
                if r["status"] == "approved"
            )
            if max_teams < approved_count:
                raise DomainValidationError(
                    f"Kuota tim tidak boleh lebih kecil dari jumlah tim yang sudah disetujui "
                    f"({approved_count} tim).",
                    {"field": "max_teams", "max_teams": max_teams, "approved_count": approved_count},
                )
            updates["max_teams"] = max_teams

        if "best_of" in payload and payload["best_of"] is not None:
            updates["best_of"] = parse_best_of(payload["best_of"])

        if "registration_fee" in payload and payload["registration_fee"] is not None:
            updates["registration_fee"] = _parse_money(
                payload["registration_fee"], "registration_fee"
            )

        if "prize_pool" in payload and payload["prize_pool"] is not None:
            updates["prize_pool"] = _parse_money(payload["prize_pool"], "prize_pool")

        if not updates and not requested_status:
            return tournament

        updated: dict[str, Any] | None = tournament
        if requested_status:
            # Execute state transition first so bracket-integrity rejection leaves zero partial field edits.
            updated = self._repo.transition_tournament_status(tournament["id"], requested_status)
            if not updated:
                raise DomainNotFoundError("Turnamen tidak ditemukan.")

        if updates:
            updated = self._repo.update_tournament(tournament["id"], updates)
            if not updated:
                raise DomainNotFoundError("Turnamen tidak ditemukan.")

        logged_details = dict(updates)
        if requested_status:
            logged_details["status"] = requested_status

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="tournament",
            entity_id=tournament["id"],
            action="TOURNAMENT_UPDATED",
            details=logged_details,
        )
        return updated

    def delete_tournament(self, actor: dict[str, Any] | None, tournament_id: str) -> dict[str, Any]:
        user = require_permission(actor, "tournament:delete")
        tournament = self.get_tournament(tournament_id)
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat menghapus turnamen miliknya sendiri."
            )
        if tournament["status"] in ("ongoing", "completed"):
            raise DomainConflictError(
                "Turnamen yang sedang berlangsung atau sudah selesai tidak dapat dihapus.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )
        self._repo.delete_tournament(tournament["id"])
        # tournament_id stays NULL so the audit entry survives the deleted parent row.
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=None,
            entity_type="tournament",
            entity_id=tournament["id"],
            action="TOURNAMENT_DELETED",
            details={
                "tournament_id": tournament["id"],
                "title": tournament["title"],
                "status": tournament["status"],
            },
        )
        return {"deleted_id": tournament["id"], "title": tournament["title"]}

    def list_registrations(
        self, tournament_id: str, actor: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        tournament = self.get_tournament(tournament_id)
        regs = self._repo.list_registrations_by_tournament(tournament["id"])
        if is_tournament_manager(self._repo, actor, tournament):
            return regs
        if (
            actor
            and actor.get("is_active", True)
            and str(actor.get("role") or "").strip().lower() == ROLE_TEAM_CAPTAIN
        ):
            actor_id = str(actor.get("id") or "")
            owned_team_ids = {
                t["id"] for t in self._repo.list_teams() if t.get("captain_id") == actor_id
            }
            return [
                r
                for r in regs
                if r.get("status") == "approved"
                or r.get("registered_by") == actor_id
                or r.get("team_id") in owned_team_ids
            ]
        return [r for r in regs if r.get("status") == "approved"]

    def register_team(
        self, actor: dict[str, Any] | None, tournament_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        user = require_permission(actor, "registration:create")
        tournament = self.get_tournament(tournament_id)

        if tournament["status"] != "open_registration":
            raise DomainConflictError(
                f"Pendaftaran ditutup untuk turnamen berstatus '{tournament['status']}'.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )

        team_id = _require_optional_text(payload.get("team_id"), "team_id")
        if not team_id:
            raise DomainValidationError("team_id wajib diisi.", {"field": "team_id"})

        team = self._repo.get_team_by_id(team_id)
        if not team:
            raise DomainNotFoundError("Tim tidak ditemukan.", {"team_id": team_id})

        if user["role"] == ROLE_TEAM_CAPTAIN and team["captain_id"] != user["id"]:
            raise DomainForbiddenError(
                "Kapten hanya dapat mendaftarkan tim miliknya sendiri.",
                {"team_id": team["id"], "user_id": user["id"]},
            )

        if team["game_id"] != tournament["game_id"]:
            raise DomainValidationError(
                "Game yang dimainkan tim tidak sesuai dengan game turnamen."
            )

        notes = _require_optional_text(payload.get("notes"), "notes")
        created = self._repo.register_team_atomic(
            tournament_id=tournament["id"],
            team_id=team["id"],
            registered_by=user["id"],
            notes=notes,
        )
        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="registration",
            entity_id=created["id"],
            action="TEAM_REGISTERED",
            details={"team_id": team["id"], "team_name": team["name"]},
        )
        return created

    def update_registration_status(
        self,
        actor: dict[str, Any] | None,
        registration_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        user = require_permission(actor, "registration:verify")
        reg = self._repo.get_registration_by_id(registration_id)
        if not reg:
            raise DomainNotFoundError(
                "Data registrasi tidak ditemukan.", {"registration_id": registration_id}
            )

        tournament = self.get_tournament(reg["tournament_id"])
        if user["role"] == ROLE_ORGANIZER and tournament["organizer_id"] != user["id"]:
            raise DomainForbiddenError(
                "Organizer hanya dapat memverifikasi registrasi pada turnamen miliknya."
            )
        if user["role"] == ROLE_COMMITTEE and not self._repo.is_staff_assigned(
            tournament["id"], user["id"]
        ):
            raise DomainForbiddenError(
                "Panitia hanya dapat memverifikasi registrasi pada turnamen yang ditugaskan."
            )

        new_status = str(payload.get("status") or "").strip().lower()
        if new_status not in REGISTRATION_STATUSES:
            raise DomainValidationError(
                f"Status registrasi '{new_status}' tidak valid.",
                {"valid_statuses": list(REGISTRATION_STATUSES)},
            )

        if tournament["status"] in REGISTRATION_LOCKED_STATUSES:
            raise DomainConflictError(
                f"Status registrasi tidak dapat diubah karena turnamen berstatus "
                f"'{tournament['status']}'.",
                {"tournament_id": tournament["id"], "status": tournament["status"]},
            )
        if self._repo.list_matches_by_tournament(tournament["id"]):
            raise DomainConflictError(
                "Status registrasi tidak dapat diubah karena bracket turnamen sudah dibuat.",
                {"tournament_id": tournament["id"]},
            )

        if new_status == "approved" and reg["status"] != "approved":
            approved_count = sum(
                1
                for r in self._repo.list_registrations_by_tournament(tournament["id"])
                if r["status"] == "approved" and r["id"] != reg["id"]
            )
            if approved_count >= int(tournament["max_teams"]):
                raise DomainConflictError(
                    f"Kuota tim yang disetujui sudah penuh ({tournament['max_teams']} tim).",
                    {
                        "tournament_id": tournament["id"],
                        "max_teams": tournament["max_teams"],
                        "approved_count": approved_count,
                    },
                )

        notes = _require_optional_text(payload.get("notes"), "notes")
        updated = self._repo.update_registration_status(
            registration_id=reg["id"],
            status=new_status,
            verified_by=user["id"],
            notes=notes,
        )
        if not updated:
            raise DomainNotFoundError("Data registrasi tidak ditemukan.")

        self._repo.log_activity(
            actor_id=user["id"],
            tournament_id=tournament["id"],
            entity_type="registration",
            entity_id=reg["id"],
            action="REGISTRATION_STATUS_UPDATED",
            details={"status": new_status, "notes": notes},
        )
        return updated
