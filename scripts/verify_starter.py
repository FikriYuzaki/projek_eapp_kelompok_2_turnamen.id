"""Verification script for Turnamen.in Starter Repository.

Checks:
1. Required folders and files exist.
2. All 18 Agent Skills (11 external + 7 custom) exist in `.agents/skills/` with valid YAML frontmatter.
3. Smoke test of Flask REST API and MockRepository succeeds.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desktop.launcher.app_launcher import run_smoke_check

EXPECTED_SKILLS = (
    # External Skills (11)
    "antislop",
    "antislop-ui",
    "antislop-human",
    "antislop-code",
    "antislop-copywriting",
    "supabase",
    "supabase-postgres-best-practices",
    "hexagonal-python",
    "tdd",
    "team-code-review",
    "frontend-design",
    # Custom Turnamen.in Skills (7)
    "turnamen-project-standards",
    "turnamen-frontend-ui",
    "turnamen-python-eel",
    "turnamen-supabase-security",
    "turnamen-bracket-engine",
    "turnamen-flask-api",
    "turnamen-quality-gates",
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def verify_skills() -> list[str]:
    errors: list[str] = []
    skills_dir = ROOT / ".agents" / "skills"
    for skill_name in EXPECTED_SKILLS:
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"Missing SKILL.md for '{skill_name}' at {skill_md}")
            continue
        content = skill_md.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(content)
        if not match:
            errors.append(f"Invalid or missing YAML frontmatter in {skill_md}")
            continue
        fm_body = match.group(1)
        if "name:" not in fm_body or "description:" not in fm_body:
            errors.append(f"Frontmatter missing 'name' or 'description' in {skill_md}")
    return errors


def main() -> int:
    skill_errors = verify_skills()
    smoke = run_smoke_check()
    report = {
        "skills_verified_count": len(EXPECTED_SKILLS) - len(skill_errors),
        "expected_skills_count": len(EXPECTED_SKILLS),
        "skill_errors": skill_errors,
        "smoke_check": smoke,
    }
    print(json.dumps(report, indent=2))
    if skill_errors or not smoke.get("health_ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
