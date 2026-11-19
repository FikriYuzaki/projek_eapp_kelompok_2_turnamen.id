"""Structured logging configuration with automatic redaction of sensitive tokens."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import re
from pathlib import Path

from backend.core.config import AppConfig, ROOT_DIR

SENSITIVE_PATTERNS = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(
        r"((?:password|passwd|secret_key|supabase_anon_key|service_role|rawg_api_key|api_key|apikey|access_token|refresh_token|auth_token|token|authorization)['\"\s:=]+)[^\s,'\"}\];&]+",
        re.IGNORECASE,
    ),
)

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def redact_sensitive_text(text: str, extra_secrets: tuple[str, ...] = ()) -> str:
    """Redact credentials, tokens, and configured secret literals from a log string."""
    if not text:
        return text
    redacted = text
    for secret in extra_secrets:
        if secret and len(secret) >= 6 and secret in redacted:
            redacted = redacted.replace(secret, "***REDACTED***")
    for pattern in SENSITIVE_PATTERNS:
        if pattern.groups >= 1:
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        else:
            redacted = pattern.sub("***REDACTED***", redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Ensure secrets, tokens, and passwords are never written to logs."""

    def __init__(self, extra_secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.extra_secrets = extra_secrets

    def update_secrets(self, extra_secrets: tuple[str, ...]) -> None:
        self.extra_secrets = extra_secrets

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = redact_sensitive_text(msg, self.extra_secrets)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


class RedactingFormatter(logging.Formatter):
    """Formatter that also redacts sensitive values from exception tracebacks."""

    def __init__(
        self,
        fmt: str,
        datefmt: str,
        redactor: SecretRedactingFilter,
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._redactor = redactor

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return redact_sensitive_text(formatted, self._redactor.extra_secrets)


def _extract_config_secrets(config: AppConfig) -> tuple[str, ...]:
    candidates = (
        getattr(config, "secret_key", ""),
        getattr(config, "supabase_anon_key", ""),
        getattr(config, "rawg_api_key", ""),
    )
    return tuple(s.strip() for s in candidates if isinstance(s, str) and s.strip())


def configure_logging(config: AppConfig) -> logging.Logger:
    """Configure application logger for console and optional rotating file output."""
    logger = logging.getLogger("turnamen_in")
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    extra_secrets = _extract_config_secrets(config)

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(level)
            for existing_filter in handler.filters:
                if isinstance(existing_filter, SecretRedactingFilter):
                    existing_filter.update_secrets(extra_secrets)
        return logger

    redactor = SecretRedactingFilter(extra_secrets=extra_secrets)
    formatter = RedactingFormatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        redactor=redactor,
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redactor)
    logger.addHandler(console_handler)

    if config.log_file:
        log_path = Path(config.log_file)
        if not log_path.is_absolute():
            log_path = ROOT_DIR / log_path
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(redactor)
            logger.addHandler(file_handler)
        except OSError:
            pass

    logger.propagate = False
    return logger
