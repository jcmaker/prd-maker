#!/usr/bin/env python3
"""Deterministic PRD.md -> single self-contained HTML converter.

The HTML is a derived view: it never introduces a fact that is not in the
source markdown. Structure parsing reuses validate_prd.py's regexes so the
linter and the converter always agree on what counts as an assumption.

Usage:
    python3 prd_to_html.py <path-to-PRD.md> [--output <path>]

Exit codes:
    0 - HTML written
    2 - usage error (bad arguments, file not found, or not valid UTF-8)
"""

import re
import sys

# Windows consoles often default to cp1252, which can't encode Korean text.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------
# Region 1 of 4: inline markdown rendering
# --------------------------------------------------------------------------

INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
# Only these href shapes are emitted as links; anything else (javascript:,
# data:, unknown schemes) is left as plain text.
SAFE_HREF_RE = re.compile(r"^(https?://|mailto:|#|\.{0,2}/|[\w.-]+\.\w)")


def escape(text):
    """Escape HTML metacharacters. Ampersand first, or later escapes double up."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _link_sub(match):
    label, href = match.group(1), match.group(2)
    if not SAFE_HREF_RE.match(href):
        return match.group(0)
    return '<a href="' + href + '">' + label + "</a>"


def render_inline(text):
    """Render the inline markdown subset a PRD uses, on already-escaped text.

    ponytail: `**bold**` inside inline code is still bolded (no tokenizer).
    Harmless in PRDs; add a real inline tokenizer if that ever matters.
    """
    out = escape(text)
    out = INLINE_CODE_RE.sub(lambda m: "<code>" + m.group(1) + "</code>", out)
    out = BOLD_RE.sub(lambda m: "<strong>" + m.group(1) + "</strong>", out)
    out = LINK_RE.sub(_link_sub, out)
    return out
