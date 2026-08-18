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


# --------------------------------------------------------------------------
# Region 2 of 4: block markdown rendering
# --------------------------------------------------------------------------

HEADING_LINE_RE = re.compile(r"^(#{1,3})\s+(.*)$")
UL_RE = re.compile(r"^[-*]\s+(.*)$")
OL_RE = re.compile(r"^\d+\.\s+(.*)$")
TASK_RE = re.compile(r"^-\s+\[([ xX])\]\s*(.*)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|\s*$")
SLUG_STRIP_RE = re.compile(r"[^\w가-힣]+")


def slugify(text, used):
    """Stable anchor id from heading text. `used` is a set of taken slugs."""
    base = SLUG_STRIP_RE.sub("-", text.strip().lower()).strip("-") or "section"
    slug, n = base, 2
    while slug in used:
        slug, n = base + "-" + str(n), n + 1
    used.add(slug)
    return slug


def _split_table_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render_blocks(lines, used_slugs=None):
    """Render markdown lines to HTML. Returns (html, headings).

    headings is a list of (level, text, anchor) for every #/##/### heading,
    in document order — the table of contents is built from it.
    """
    used = used_slugs if used_slugs is not None else set()
    out, headings = [], []
    i, n = 0, len(lines)

    def close(stack):
        while stack:
            out.append("</" + stack.pop() + ">")

    open_tags = []
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            close(open_tags)
            fence = stripped[:3]
            body, i = [], i + 1
            while i < n and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            out.append("<pre><code>" + escape("\n".join(body)) + "</code></pre>")
            continue

        if stripped == "":
            close(open_tags)
            i += 1
            continue

        m = HEADING_LINE_RE.match(stripped)
        if m:
            close(open_tags)
            level, text = len(m.group(1)), m.group(2).strip()
            anchor = slugify(text, used)
            headings.append((level, text, anchor))
            out.append(
                "<h%d id=\"%s\">%s</h%d>" % (level, anchor, render_inline(text), level)
            )
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1].strip()):
            close(open_tags)
            head = _split_table_row(stripped)
            out.append('<div class="scroll"><table><tr>')
            out.extend("<th>" + render_inline(c) + "</th>" for c in head)
            out.append("</tr>")
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                out.append("<tr>")
                out.extend(
                    "<td>" + render_inline(c) + "</td>"
                    for c in _split_table_row(lines[i].strip())
                )
                out.append("</tr>")
                i += 1
            out.append("</table></div>")
            continue

        m = TASK_RE.match(stripped)
        if m:
            if open_tags[-1:] != ["ul"]:
                close(open_tags)
                out.append('<ul class="crit">')
                open_tags.append("ul")
            checked = m.group(1).lower() == "x"
            mark = "☑" if checked else "☐"
            cls = "done" if checked else "todo"
            out.append(
                '<li class="%s"><span class="mark">%s</span> %s</li>'
                % (cls, mark, render_inline(m.group(2)))
            )
            i += 1
            continue

        m = OL_RE.match(stripped)
        if m:
            if open_tags[-1:] != ["ol"]:
                close(open_tags)
                out.append("<ol>")
                open_tags.append("ol")
            out.append("<li>" + render_inline(m.group(1)) + "</li>")
            i += 1
            continue

        m = UL_RE.match(stripped)
        if m:
            if open_tags[-1:] != ["ul"]:
                close(open_tags)
                out.append("<ul>")
                open_tags.append("ul")
            out.append("<li>" + render_inline(m.group(1)) + "</li>")
            i += 1
            continue

        m = QUOTE_RE.match(stripped)
        if m:
            if open_tags[-1:] != ["blockquote"]:
                close(open_tags)
                out.append("<blockquote>")
                open_tags.append("blockquote")
            out.append(render_inline(m.group(1)) + " ")
            i += 1
            continue

        close(open_tags)
        out.append("<p>" + render_inline(stripped) + "</p>")
        i += 1

    close(open_tags)
    return "\n".join(out), headings
