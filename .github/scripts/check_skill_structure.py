#!/usr/bin/env python3
"""Structural integrity checks for every skill in skills/.

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
SKILLS_ROOT = ROOT / "skills"

SKILL_MAX_LINES = 150
DESCRIPTION_MAX_CHARS = 1024  # Claude Agent Skills frontmatter limit

# A skill may point at a sibling skill's asset rather than duplicating it, in
# either of the two forms the skills actually use: `../other-skill/scripts/x.py`
# or the Claude Code plugin-root form. Both prefixes are part of the path we
# resolve — matching only from `scripts/` onward would resolve against the
# wrong skill directory and pass or fail for the wrong reason.
PLUGIN_ROOT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/"
REFERENCE_RE = re.compile(
    r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/skills/[A-Za-z0-9_-]+/|\.\./[A-Za-z0-9_-]+/)?"
    r"(?:references|scripts)/[A-Za-z0-9_./-]+\.(?:md|py)"
)


def resolve_reference(skill_dir, rel):
    """Resolve a referenced path to a real file location.

    Plugin-root paths are repo-absolute; everything else is relative to the
    skill that named it.
    """
    if rel.startswith(PLUGIN_ROOT_PREFIX):
        return (ROOT / rel[len(PLUGIN_ROOT_PREFIX):]).resolve()
    return (skill_dir / rel).resolve()


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


def check_skill_md(skill_dir):
    """Line cap and frontmatter. The declared name must match the directory,
    which is what every agent uses to address the skill."""
    ok = True
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")

    line_count = len(text.splitlines())
    if line_count > SKILL_MAX_LINES:
        ok = fail(f"{skill_dir.name}/SKILL.md is {line_count} lines (max {SKILL_MAX_LINES}).")
    else:
        print(f"PASS - {skill_dir.name}/SKILL.md line count: {line_count} (<= {SKILL_MAX_LINES}).")

    fields = parse_frontmatter(text)
    if fields is None:
        return fail(f"{skill_dir.name}/SKILL.md has no valid YAML frontmatter block.")

    for key in ("name", "description"):
        if not fields.get(key):
            ok = fail(f"{skill_dir.name}/SKILL.md frontmatter is missing '{key}'.")
    if fields.get("name") and fields["name"] != skill_dir.name:
        ok = fail(
            f"{skill_dir.name}/SKILL.md frontmatter name is '{fields['name']}', "
            f"expected '{skill_dir.name}' to match its directory."
        )
    desc_len = len(fields.get("description", ""))
    if desc_len > DESCRIPTION_MAX_CHARS:
        ok = fail(
            f"{skill_dir.name}/SKILL.md description is {desc_len} chars "
            f"(max {DESCRIPTION_MAX_CHARS})."
        )
    if ok:
        print(f"PASS - {skill_dir.name}/SKILL.md frontmatter valid (description {desc_len} chars).")

    return ok


def check_referenced_files(skill_dir):
    """Every references/*.md and scripts/*.py named in SKILL.md must exist."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    referenced = set(REFERENCE_RE.findall(text))
    if not referenced:
        print(f"PASS - {skill_dir.name}: no reference paths named (nothing to verify).")
        return True

    ok = True
    for rel in sorted(referenced):
        target = resolve_reference(skill_dir, rel)
        if target.exists():
            print(f"PASS - {skill_dir.name}: referenced file exists: {rel}")
        else:
            ok = fail(
                f"{skill_dir.name}/SKILL.md references '{rel}' but {target} does not exist."
            )
    return ok


def main():
    skill_dirs = sorted(d for d in SKILLS_ROOT.iterdir() if (d / "SKILL.md").is_file())
    if not skill_dirs:
        print(f"FAIL - no skills with a SKILL.md found under {SKILLS_ROOT}")
        return 1

    print(f"== skill structure checks ({len(skill_dirs)} skill(s)) ==")
    results = []
    for skill_dir in skill_dirs:
        results.append(check_skill_md(skill_dir))
        results.append(check_referenced_files(skill_dir))

    if all(results):
        print("\nAll structure checks passed.")
        return 0
    print("\nStructure checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
