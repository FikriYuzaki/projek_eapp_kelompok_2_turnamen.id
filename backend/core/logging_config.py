"""Structured logging configuration with automatic redaction of sensitive tokens."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.core.config import AppConfig, ROOT_DIR

SENSITIVE_PATTERNS = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"(password['\"\s:=]+)[^\s,'\"}]+", re.IGNORECASE),
    re.compile(r"(secret_key['\"\s:=]+)[^\s,'\"}]+", re.IGNORECASE),
    re.compile(r"(supabase_anon_key['\"\s:=]+)[^\s,'\"}]+", re.IGNORECASE),
    re.compile(r"(service_role['\"\s:=]+)[^\s,'\"}]+", re.IGNORECASE),
)


class SecretRedactingFilter(logging.Filter):
    """Ensure secrets, tokens, and passwords are never written to logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = msg
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(config: AppConfig) -> logging.Logger:
    """Configure application logger for console and optional rotating file output."""
    logger = logging.getLogger("turnamen_in")
    if logger.handlers:
        return logger

    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redactor = SecretRedactingFilter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redactor)
    logger.addHandler(console_handler)

    if config.log_file:
        log_path = ROOT_DIR / config.log_file
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.addFilter(redactor)
            logger.addHandler(file_handler)
        except OSError:
            pass

    logger.propagate = False
    return logger
