"""Shared domain constants, role definitions, and status enumerations."""

from __future__ import annotations

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ORGANIZER = "organizer"
ROLE_COMMITTEE = "committee"
ROLE_TEAM_CAPTAIN = "team_captain"
ROLE_PLAYER = "player"

ALL_ROLES = (
    ROLE_SUPER_ADMIN,
    ROLE_ORGANIZER,
    ROLE_COMMITTEE,
    ROLE_TEAM_CAPTAIN,
    ROLE_PLAYER,
)

SELF_REGISTRABLE_ROLES = (
    ROLE_PLAYER,
    ROLE_TEAM_CAPTAIN,
)

TOURNAMENT_STATUSES = (
    "draft",
    "open_registration",
    "registration_closed",
    "ongoing",
    "completed",
    "cancelled",
)

REGISTRATION_STATUSES = (
    "pending",
    "approved",
    "rejected",
    "withdrawn",
)

MATCH_STATUSES = (
    "scheduled",
    "ongoing",
    "completed",
    "bye",
    "disputed",
)

ANNOUNCEMENT_PRIORITIES = (
    "normal",
    "important",
    "urgent",
)

VALID_BEST_OF = (1, 3, 5, 7)
