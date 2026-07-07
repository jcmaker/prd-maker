#!/usr/bin/env python3
"""Deterministic structure linter for PRD.md files produced by the prd-maker skill.

Checks are language-agnostic: they match markdown structure and numbers only,
never heading words, because the generated PRD is written in the user's language.
Fenced code blocks (``` ... ```) are stripped before all checks — including the
ASSUMPTIONS listing — so markdown examples inside the PRD cannot cause false
failures.

Usage:
    python3 validate_prd.py <path-to-PRD.md>

Exit codes:
    0 - all 5 structural checks pass
    1 - at least one check failed
    2 - usage error (missing argument, file not found, or not valid UTF-8)
"""

import re
import sys
from pathlib import Path

# Windows consoles often default to cp1252, which can't encode Korean text.
# Force UTF-8 for stdout/stderr so the linter works cross-platform.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

HEADING_RE = re.compile(r"^## ")
NUMBERED_SECTION_RE = re.compile(r"^## ([1-7])\.")
NON_GOAL_ITEM_RE = re.compile(r"^(?:- |\* )")
PHASE_RE = re.compile(r"^### ")
CHECKBOX_RE = re.compile(r"^- \[[ xX]\]")
NUMBERED_ITEM_RE = re.compile(r"^\d+\.")
ASSUMPTION_RE = re.compile(r"\(가정\)|\(assumption\)", re.IGNORECASE)

REQUIRED_SECTIONS = list(range(1, 8))
MIN_NON_GOALS = 3
MAX_REQUIREMENTS_PER_PHASE = 50
ADVISORY_REQUIREMENTS_THRESHOLD = 30



def strip_fenced_blocks(lines):
    """Blank out lines inside fenced code blocks (and the ``` fence lines
    themselves), keeping list indices stable so reported line numbers stay
    correct.
    """
    stripped = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            stripped.append("")
        else:
            stripped.append("" if in_fence else line)
    return stripped


def find_section_body(lines, section_num):
    """Return the body lines (list of (line_no, text)) of `## <section_num>.` up
    to (but not including) the next `## ` heading, or None if the heading is
    not present.
    """
    heading_re = re.compile(r"^## " + str(section_num) + r"\.")
    start = None
    for i, line in enumerate(lines):
        if heading_re.match(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEADING_RE.match(lines[i]):
            end = i
            break
    return [(idx + 1, lines[idx]) for idx in range(start + 1, end)]


def find_phase_blocks(section_body):
    """Given a section's body lines (list of (line_no, text)), return a list of
    (phase_title, block_lines) for each `### ` phase heading found. block_lines
    is the list of (line_no, text) belonging to that phase, up to the next
    `### ` or end of section body.
    """
    phases = []
    current_title = None
    current_block = []
    for line_no, text in section_body:
        if PHASE_RE.match(text):
            if current_title is not None:
                phases.append((current_title, current_block))
            current_title = text[len("### "):].strip()
            current_block = []
        else:
            if current_title is not None:
                current_block.append((line_no, text))
    if current_title is not None:
        phases.append((current_title, current_block))
    return phases


def check1_agent_header(lines):
    non_empty = [(i + 1, l) for i, l in enumerate(lines) if l.strip() != ""]
    first_five = non_empty[:5]
    for line_no, text in first_five:
        if text.strip().startswith("> "):
            return True, f"blockquote header found on line {line_no}."
    return (
        False,
        "no blockquote line (`> ...`) found within the first 5 non-empty lines.",
    )


def check2_seven_sections(lines):
    found = []  # list of (number, line_no) in document order
    for i, line in enumerate(lines):
        m = NUMBERED_SECTION_RE.match(line)
        if m:
            found.append((int(m.group(1)), i + 1))

    numbers_in_order = [n for n, _ in found]
    seen_counts = {}
    for n, _ in found:
        seen_counts[n] = seen_counts.get(n, 0) + 1

    missing = [n for n in REQUIRED_SECTIONS if n not in seen_counts]
    duplicated = sorted(n for n, c in seen_counts.items() if c > 1)
    out_of_order = numbers_in_order != sorted(numbers_in_order)

    if not missing and not duplicated and not out_of_order:
        return True, "sections 1-7 each present exactly once, in ascending order."

    details = []
    if missing:
        details.append(f"missing: {missing}")
    if duplicated:
        details.append(f"duplicated: {duplicated}")
    if out_of_order:
        details.append(f"out of order: found order {numbers_in_order}")
    return False, "; ".join(details)


def check3_non_goals(lines):
    body = find_section_body(lines, 4)
    if body is None:
        return False, "section `## 4.` not found."
    count = sum(1 for _, text in body if NON_GOAL_ITEM_RE.match(text))
    if count >= MIN_NON_GOALS:
        return True, f"{count} non-goal items found (>= {MIN_NON_GOALS})."
    return (
        False,
        f"only {count} non-goal item(s) found in `## 4.` (need >= {MIN_NON_GOALS}).",
    )


def check4_phase_checkboxes(lines):
    """Every `### ` heading inside section 6 is treated as a phase by design:
    the PRD template allows only phase headings at that level within section 6.
    """
    body = find_section_body(lines, 6)
    if body is None:
        return False, "section `## 6.` not found."
    phases = find_phase_blocks(body)
    if not phases:
        return False, "no phases (`### ` headings) found in `## 6.`."

    missing_checkbox_phases = []
    for title, block in phases:
        has_checkbox = any(CHECKBOX_RE.match(text) for _, text in block)
        if not has_checkbox:
            missing_checkbox_phases.append(title)

    if not missing_checkbox_phases:
        return True, f"{len(phases)} phase(s) found, each with >= 1 checkbox."
    return (
        False,
        "phase(s) without any checkbox acceptance criteria: "
        + ", ".join(missing_checkbox_phases),
    )


def check5_requirements_cap(lines):
    body = find_section_body(lines, 6)
    if body is None:
        return False, "section `## 6.` not found.", []
    phases = find_phase_blocks(body)
    if not phases:
        return False, "no phases (`### ` headings) found in `## 6.`.", []

    over_cap = []
    advisories = []
    for title, block in phases:
        count = sum(1 for _, text in block if NUMBERED_ITEM_RE.match(text))
        if count > MAX_REQUIREMENTS_PER_PHASE:
            over_cap.append((title, count))
        elif count > ADVISORY_REQUIREMENTS_THRESHOLD:
            advisories.append((title, count))

    if not over_cap:
        return (
            True,
            f"all {len(phases)} phase(s) have <= {MAX_REQUIREMENTS_PER_PHASE} requirements.",
            advisories,
        )
    detail = ", ".join(
        f"'{title}' has {count} requirements (max {MAX_REQUIREMENTS_PER_PHASE})"
        for title, count in over_cap
    )
    return False, detail, advisories


def find_assumptions(lines):
    return [
        (i + 1, line.strip())
        for i, line in enumerate(lines)
        if ASSUMPTION_RE.search(line)
    ]


def run_checks(text):
    lines = strip_fenced_blocks(text.splitlines())

    check5_passed, check5_detail, check5_advisories = check5_requirements_cap(lines)

    checks = [
        ("CHECK 1 (agent header)", check1_agent_header(lines)),
        ("CHECK 2 (seven numbered sections)", check2_seven_sections(lines)),
        ("CHECK 3 (non-goals count)", check3_non_goals(lines)),
        ("CHECK 4 (phases + acceptance checkboxes)", check4_phase_checkboxes(lines)),
        ("CHECK 5 (requirements cap)", (check5_passed, check5_detail)),
    ]

    report_lines = []
    all_pass = True
    for name, (passed, detail) in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        report_lines.append(f"{status} - {name}: {detail}")

    for title, count in check5_advisories:
        report_lines.append(
            f'ADVISORY - Phase "{title}" has {count} requirements '
            f"(recommended <= {ADVISORY_REQUIREMENTS_THRESHOLD})"
        )

    assumptions = find_assumptions(lines)
    report_lines.append(f"ASSUMPTIONS ({len(assumptions)}):")
    for line_no, text_line in assumptions:
        report_lines.append(f"  L{line_no}: {text_line}")

    return all_pass, "\n".join(report_lines)


def main(argv):
    if len(argv) != 2:
        print("Usage: python3 validate_prd.py <path-to-PRD.md>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"Error: {path} is not valid UTF-8 text.", file=sys.stderr)
        return 2

    all_pass, report = run_checks(text)
    print(report)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
