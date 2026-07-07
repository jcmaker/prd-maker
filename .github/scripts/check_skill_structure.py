#!/usr/bin/env python3
"""Structural integrity checks for the prd-maker skill.

Guards the documented constraints that the unit tests (which cover the PRD
linter's behavior) do not: the SKILL.md line cap, valid frontmatter, and that
every referenced file actually exists. Language-agnostic, stdlib only.

Usage: python3 .github/scripts/check_skill_structure.py
Exit 0 if all checks pass, 1 otherwise.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "prd-maker"
SKILL_MD = SKILL_DIR / "SKILL.md"

SKILL_MAX_LINES = 150
DESCRIPTION_MAX_CHARS = 1024  # Claude Agent Skills frontmatter limit


def fail(msg):
    print(f"FAIL - {msg}")
    return False


def parse_frontmatter(text):
    """Return the YAML frontmatter block as a dict of top-level string keys."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if km:
            fields[km.group(1)] = km.group(2)
    return fields


def check_skill_md():
    ok = True
    if not SKILL_MD.exists():
        return fail(f"{SKILL_MD} does not exist")

    text = SKILL_MD.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    if line_count > SKILL_MAX_LINES:
        ok = fail(f"SKILL.md is {line_count} lines (max {SKILL_MAX_LINES}).")
    else:
        print(f"PASS - SKILL.md line count: {line_count} (<= {SKILL_MAX_LINES}).")

    fields = parse_frontmatter(text)
    if fields is None:
        return fail("SKILL.md has no valid YAML frontmatter block.")

    for key in ("name", "description"):
        if not fields.get(key):
            ok = fail(f"SKILL.md frontmatter is missing '{key}'.")
    if fields.get("name") and fields["name"] != "prd-maker":
        ok = fail(f"SKILL.md frontmatter name is '{fields['name']}', expected 'prd-maker'.")
    desc_len = len(fields.get("description", ""))
    if desc_len > DESCRIPTION_MAX_CHARS:
        ok = fail(f"SKILL.md description is {desc_len} chars (max {DESCRIPTION_MAX_CHARS}).")
    if ok:
        print(f"PASS - SKILL.md frontmatter valid (description {desc_len} chars).")

    return ok


def check_referenced_files():
    """Every references/*.md and scripts/*.py named in SKILL.md must exist."""
    text = SKILL_MD.read_text(encoding="utf-8")
    referenced = set(re.findall(r"(?:references|scripts)/[A-Za-z0-9_./-]+\.(?:md|py)", text))
    if not referenced:
        print("PASS - no reference paths named in SKILL.md (nothing to verify).")
        return True

    ok = True
    for rel in sorted(referenced):
        target = SKILL_DIR / rel
        if target.exists():
            print(f"PASS - referenced file exists: {rel}")
        else:
            ok = fail(f"SKILL.md references '{rel}' but {target} does not exist.")
    return ok


def main():
    print("== prd-maker skill structure checks ==")
    results = [check_skill_md(), check_referenced_files()]
    if all(results):
        print("\nAll structure checks passed.")
        return 0
    print("\nStructure checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
