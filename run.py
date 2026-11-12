"""Turnamen.in — Unified Application Entry Point (`run.py`).

Owner: Fikri (System Integration & Python Eel Developer)

Usage:
    python run.py              # Launch Flask REST API + Python Eel Desktop Window
    python run.py --api-only   # Run local Flask REST API + Web UI on http://127.0.0.1:5000
    python run.py --check      # Run non-interactive smoke check of config, mock repo, and API
"""

from __future__ import annotations

import argparse
import json
import sys

from backend.core.config import load_config
from desktop.launcher.app_launcher import launch_application, run_smoke_check


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Turnamen.in — Esports Tournament Management System Launcher",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only the local Flask REST API and Web UI server without opening an Eel window.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify configuration, mock repository, and API health, then exit.",
    )
    parser.add_argument(
        "--mode",
        choices=("mock", "supabase"),
        default=None,
        help="Override APP_MODE ('mock' or 'supabase'). Defaults to .env or 'mock'.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override local Flask API port (default: 5000).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    overrides: dict[str, object] = {}
    if args.mode is not None:
        overrides["app_mode"] = args.mode
    if args.port is not None:
        overrides["api_port"] = args.port

    try:
        config = load_config(overrides=overrides or None)
    except ValueError as exc:
        if args.check:
            print(
                json.dumps(
                    {
                        "config": None,
                        "health_ok": False,
                        "repository_ok": False,
                        "games_count": 0,
                        "tournaments_count": 0,
                        "error": str(exc),
                    },
                    indent=2,
                )
            )
            return 1
        print(f"Error konfigurasi: {exc}", file=sys.stderr)
        return 1

    if args.check:
        summary = run_smoke_check(config)
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("health_ok") else 1

    try:
        return launch_application(api_only=args.api_only, config=config)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
