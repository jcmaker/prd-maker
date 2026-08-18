#!/usr/bin/env python3
"""Deterministic PRD.md -> single self-contained HTML converter.

The HTML is a derived view: it never introduces a fact that is not in the
source markdown. Structure parsing reuses validate_prd.py's regexes so the
linter and the converter always agree on what counts as an assumption.

Usage:
    python3 prd_to_html.py <path-to-PRD.md> [--output <path>]

Exit codes:
    0 - HTML written
    2 - usage error (bad arguments, file not found, not valid UTF-8, or an
        --output path that cannot be written)
"""

import re
import sys
from datetime import datetime
from pathlib import Path

from validate_prd import (
    CHECKBOX_RE,
    NON_GOAL_ITEM_RE,
    NUMBERED_ITEM_RE,
    PHASE_RE,
    find_assumptions,
    find_phase_blocks,
    find_section_body,
    strip_fenced_blocks,
)

# Windows consoles often default to cp1252, which can't encode Korean text.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------
# Region 1 of 5: inline markdown rendering
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
# Region 2 of 5: block markdown rendering
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


def render_blocks(lines, used_slugs=None, ids=None):
    """Render markdown lines to HTML. Returns (html, headings).

    headings is a list of (level, text, anchor) for every #/##/### heading,
    in document order — the table of contents is built from it.

    `ids` optionally maps a line index to a `{"id": ..., "anchor": ...}` record;
    the list item rendered from that line gets the anchor as its HTML id and the
    id printed beside it. Section 6 uses it to attach `P1-R2` / `P1-A3` labels
    without taking the content away from this renderer.
    """
    used = used_slugs if used_slugs is not None else set()

    def decorate(index):
        """(id attribute, visible id label) for the item on this line."""
        item = ids.get(index) if ids else None
        if not item:
            return "", ""
        return (
            ' id="%s"' % item["anchor"],
            '<span class="rid">%s</span> ' % escape(item["id"]),
        )

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
            attr, rid = decorate(i)
            out.append(
                '<li%s class="%s"><span class="mark">%s</span> %s%s</li>'
                % (attr, cls, mark, rid, render_inline(m.group(2)))
            )
            i += 1
            continue

        m = OL_RE.match(stripped)
        if m:
            if open_tags[-1:] != ["ol"]:
                close(open_tags)
                out.append("<ol>")
                open_tags.append("ol")
            attr, rid = decorate(i)
            out.append(
                "<li%s>%s%s</li>" % (attr, rid, render_inline(m.group(1)))
            )
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


def split_phase_chunks(chunk_lines):
    """Split raw section-6 lines into (pre_phase_lines, [(offset, lines), ...]).

    `offset` is the index in `chunk_lines` of the group's first body line, so a
    caller holding absolute line numbers can address into the group.

    The split rule mirrors `validate_prd.find_phase_blocks` exactly — `### ` at
    column 0, outside fenced blocks — so the groups line up one-for-one with
    what `collect_phases` parsed. Nothing is dropped: every line lands either in
    the pre-phase list or in a phase group.
    """
    pre, groups = [], []
    fence = None
    for i, line in enumerate(chunk_lines):
        bucket = groups[-1][1] if groups else pre
        stripped = line.lstrip()
        if fence is not None:
            bucket.append(line)
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            bucket.append(line)
            continue
        if PHASE_RE.match(line):
            groups.append((i + 1, []))  # the heading itself is rendered by caller
            continue
        bucket.append(line)
    return pre, groups


def render_phase_section(chunk_lines, chunk_start, phases, used_slugs):
    """Render section 6 as a timeline of phase cards.

    Bodies go through `render_blocks` on the *raw* lines, so source order,
    prose before the first phase, tables, and fenced code all survive; the only
    thing the parsed model contributes is the `P1-R2` / `P1-A3` anchors, keyed
    by source line number. `chunk_start` is the 1-based source line of
    `chunk_lines[0]`.
    """
    pre_lines, groups = split_phase_chunks(chunk_lines)
    if len(groups) != len(phases):
        # Should not happen — same split rule as the parser. If it ever does,
        # render everything plainly rather than dropping a phase.
        return render_blocks(chunk_lines, used_slugs)

    html, headings = render_blocks(pre_lines, used_slugs)
    out = [html, '<ol class="tl">']
    for ph, (offset, lines) in zip(phases, groups):
        used_slugs.add(ph["anchor"])
        headings.append((3, ph["title"], ph["anchor"]))
        ids = {
            item["line"] - chunk_start - offset: item
            for item in ph["requirements"] + ph["criteria"]
        }
        body, sub_headings = render_blocks(lines, used_slugs, ids)
        headings.extend(sub_headings)
        out.append(
            '<li class="phase"><h3 id="%s">%s</h3>'
            % (ph["anchor"], escape(ph["title"]))
        )
        out.append(body)
        out.append("</li>")
    out.append("</ol>")
    return "\n".join(out), headings


# --------------------------------------------------------------------------
# Region 3 of 5: structure parsing (reuses validate_prd's regexes)
# --------------------------------------------------------------------------

SECTION_HEADING_RE = re.compile(r"^##\s+(?:(\d+)\.)?")
NUMBER_PREFIX_RE = re.compile(r"^\d+\.\s*")


def detect_lang(text):
    """Guess the document language from the Hangul share of its letters."""
    hangul = sum(1 for ch in text if "가" <= ch <= "힣")
    letters = sum(1 for ch in text if ch.isalpha())
    return "ko" if letters and hangul / letters > 0.3 else "en"


def extract_title(lines, fallback):
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def collect_non_goals(stripped_lines):
    body = find_section_body(stripped_lines, 4)
    if body is None:
        return []
    return [
        text.strip().lstrip("-*").strip()
        for _, text in body
        if NON_GOAL_ITEM_RE.match(text)
    ]


def collect_phases(stripped_lines):
    """Phases of section 6, with stable IDs for requirements and criteria.

    This is an index over the source, not a replacement for it: each item keeps
    its 1-based source `line` so the renderer can attach the id to the element
    it renders from that same line, in source order.
    """
    body = find_section_body(stripped_lines, 6)
    if body is None:
        return []
    phases = []
    for index, (title, block) in enumerate(find_phase_blocks(body), start=1):
        reqs, crits = [], []
        for line_no, text in block:
            content = text.strip()
            if not content:
                continue
            m = CHECKBOX_RE.match(content)
            if m:
                k = len(crits) + 1
                crits.append(
                    {
                        "id": "P%d-A%d" % (index, k),
                        "anchor": "p%d-a%d" % (index, k),
                        "line": line_no,
                        "text": content[len(m.group(0)):].strip(),
                        "checked": "x" in m.group(0).lower(),
                    }
                )
            elif NUMBERED_ITEM_RE.match(content):
                k = len(reqs) + 1
                reqs.append(
                    {
                        "id": "P%d-R%d" % (index, k),
                        "anchor": "p%d-r%d" % (index, k),
                        "line": line_no,
                        "text": NUMBER_PREFIX_RE.sub("", content).strip(),
                    }
                )
        phases.append(
            {
                "index": index,
                "title": title,
                "anchor": "phase-%d" % index,
                "requirements": reqs,
                "criteria": crits,
            }
        )
    return phases


def split_sections(raw_lines):
    """Split raw lines at every `## ` heading. The preamble chunk has num=None.

    Each chunk records `start`, the 1-based source line of its first line.
    """
    chunks = [{"num": None, "start": 1, "lines": []}]
    in_fence = False
    fence = None
    for i, line in enumerate(raw_lines):
        stripped = line.strip()
        if in_fence:
            if stripped.startswith(fence):
                in_fence = False
            chunks[-1]["lines"].append(line)
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence, fence = True, stripped[:3]
            chunks[-1]["lines"].append(line)
            continue
        m = SECTION_HEADING_RE.match(stripped)
        if m:
            num = int(m.group(1)) if m.group(1) else None
            chunks.append({"num": num, "start": i + 1, "lines": [line]})
        else:
            chunks[-1]["lines"].append(line)
    return [c for c in chunks if any(x.strip() for x in c["lines"])]


def drop_title_line(lines):
    """Remove the first top-level `# ` line, outside fences.

    The header already prints the title; rendering it again would give the page
    two `<h1>` elements. Mirrors `extract_title`'s match so exactly the line the
    title came from is the line dropped.
    """
    out, fence, dropped = [], None, False
    for line in lines:
        stripped = line.lstrip()
        if fence is not None:
            out.append(line)
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            out.append(line)
            continue
        if not dropped and line.startswith("# "):
            dropped = True
            continue
        out.append(line)
    return out


def parse_document(text, fallback_title):
    raw = text.splitlines()
    stripped = strip_fenced_blocks(raw)
    phases = collect_phases(stripped)

    used_slugs = set()
    headings, parts = [], []
    for position, chunk in enumerate(split_sections(raw)):
        num = chunk["num"]
        if num == 6 and phases:
            html, hs = render_phase_section(
                chunk["lines"], chunk["start"], phases, used_slugs
            )
        else:
            lines = chunk["lines"]
            if position == 0 and num is None:
                lines = drop_title_line(lines)
            html, hs = render_blocks(lines, used_slugs)
        if num:
            attrs = 'class="sec sec-%d" id="s%d"' % (num, num)
        else:
            attrs = 'class="sec"'
        parts.append("<section %s>%s</section>" % (attrs, html))
        headings.extend(hs)

    return {
        # Title extraction is structure parsing, so it reads the fence-stripped
        # lines: a `# ` inside a fenced example must not become the document title.
        "title": extract_title(stripped, fallback_title),
        "lang": detect_lang(text),
        "headings": headings,
        "assumptions": find_assumptions(stripped),
        "non_goals": collect_non_goals(stripped),
        "phases": phases,
        "sections_html": "\n".join(parts),
    }


# --------------------------------------------------------------------------
# Region 4 of 5: HTML template assembly
# --------------------------------------------------------------------------

STYLE = """
:root{--bg:#fff;--surface:#f7f8fa;--text:#1a1d21;--muted:#5f6670;--border:#e2e6ea;
--accent:#1d4ed8;--warn-bd:#c2870a;--warn-bg:#fdf6e3;--stop-bd:#b4453c;
--stop-bg:#fdf0ef;--code-bg:#f2f4f7}
:root[data-theme="dark"]{--bg:#14171a;--surface:#1b1f24;--text:#e6e8ea;--muted:#9aa3ad;
--border:#2b3138;--accent:#7ea6ff;--warn-bd:#c99a2e;--warn-bg:#26210f;
--stop-bd:#cc6b62;--stop-bg:#2a1715;--code-bg:#1f242a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#14171a;--surface:#1b1f24;--text:#e6e8ea;--muted:#9aa3ad;--border:#2b3138;
--accent:#7ea6ff;--warn-bd:#c99a2e;--warn-bg:#26210f;--stop-bd:#cc6b62;
--stop-bg:#2a1715;--code-bg:#1f242a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-size:17px;line-height:1.7;
word-break:keep-all;overflow-wrap:anywhere;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
.skip{position:absolute;left:-9999px}
.skip:focus{left:8px;top:8px;background:var(--accent);color:#fff;padding:8px 12px;z-index:9}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
main{max-width:64ch}
h1{font-size:1.9rem;line-height:1.35;margin:0 0 6px}
h2{font-size:1.28rem;margin:2.4em 0 .6em;scroll-margin-top:16px}
h3{font-size:1.05rem;margin:1.6em 0 .4em;scroll-margin-top:16px}
a{color:var(--accent)}
code{background:var(--code-bg);padding:.1em .35em;border-radius:4px;font-size:.88em}
header.doc{border-bottom:1px solid var(--border);padding:28px 0 18px}
.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted);font-size:.83rem;margin-top:10px}
.toggle{background:var(--surface);color:var(--text);border:1px solid var(--border);
border-radius:999px;padding:5px 13px;font-size:.8rem;cursor:pointer;font-family:inherit}
.dash{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:10px;margin:22px 0 8px}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;
padding:12px 14px;text-decoration:none;color:inherit;display:block;break-inside:avoid}
.tile .n{font-size:1.55rem;font-weight:700;display:block;line-height:1.2}
.tile .l{font-size:.76rem;color:var(--muted);display:block}
.tile.warn{background:var(--warn-bg);border-color:var(--warn-bd)}
.panel{border:1px solid var(--border);border-left-width:4px;border-radius:8px;
padding:14px 18px;margin:18px 0;background:var(--surface);break-inside:avoid}
.panel.assume{border-left-color:var(--warn-bd);background:var(--warn-bg)}
.panel h2{margin:0 0 .3em;font-size:1rem}
.sec-3 ol>li{background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:10px 14px;margin:.5em 0;break-inside:avoid}
.sec-4 ul{border:1px solid var(--stop-bd);background:var(--stop-bg);
border-radius:8px;padding:12px 18px 12px 34px;break-inside:avoid}
table{border-collapse:collapse;width:100%;margin:1.1em 0;font-size:.92rem;break-inside:avoid}
th,td{border:1px solid var(--border);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--surface);font-weight:600}
.scroll{overflow-x:auto}
pre{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;
padding:12px 14px;overflow-x:auto;font-size:.83rem;break-inside:avoid}
blockquote{border-left:3px solid var(--accent);margin:1em 0;padding:.2em 0 .2em 14px;color:var(--muted)}
.tl{list-style:none;padding:0;margin:1.2em 0;position:relative}
.tl:before{content:"";position:absolute;left:11px;top:6px;bottom:6px;width:2px;background:var(--border)}
.tl>li{position:relative;padding:0 0 16px 34px;break-inside:avoid}
.tl>li:before{content:"";position:absolute;left:5px;top:14px;width:14px;height:14px;
border-radius:50%;background:var(--bg);border:2px solid var(--accent)}
.crit{list-style:none;padding-left:0}
.crit .mark{margin-right:6px}
.rid{font-size:.74rem;color:var(--muted);font-variant-numeric:tabular-nums;margin-right:6px}
footer.doc{border-top:1px solid var(--border);margin-top:48px;padding:18px 0 40px;
color:var(--muted);font-size:.83rem}
nav.toc{display:none}
details.mtoc{margin:16px 0;border:1px solid var(--border);border-radius:8px;
padding:8px 14px;background:var(--surface)}
@media (min-width:1024px){
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:44px;align-items:start}
nav.toc{display:block;position:sticky;top:20px;font-size:.85rem;max-height:92vh;overflow-y:auto}
nav.toc ol{list-style:none;margin:0;padding:0}
nav.toc a{display:block;padding:3px 0 3px 10px;border-left:2px solid var(--border);
color:var(--muted);text-decoration:none}
nav.toc a.active{color:var(--accent);border-left-color:var(--accent);font-weight:600}
details.mtoc{display:none}}
@media print{
:root{--bg:#fff;--surface:#fff;--text:#000;--muted:#333;--border:#999;--accent:#000;
--warn-bg:#fff;--stop-bg:#fff;--code-bg:#fff}
nav.toc,.toggle,details.mtoc{display:none!important}
body{font-size:11pt;line-height:1.5}
.layout{display:block}
main{max-width:none}
a[href^="http"]:after{content:" (" attr(href) ")";font-size:.85em}
h2,h3{page-break-after:avoid}
.tile,.panel,table,pre,.tl>li{page-break-inside:avoid}
@page{margin:18mm}}
"""

SCRIPT = """
(function(){
var r=document.documentElement,b=document.getElementById('themeToggle');
if(b){b.addEventListener('click',function(){
var c=r.getAttribute('data-theme');
if(!c){c=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';}
r.setAttribute('data-theme',c==='dark'?'light':'dark');});}
var links={},as=document.querySelectorAll('nav.toc a');
as.forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
if(!as.length)return;
var io=new IntersectionObserver(function(es){es.forEach(function(e){
var a=links[e.target.id];if(!a)return;
if(e.isIntersecting){as.forEach(function(x){x.classList.remove('active');});
a.classList.add('active');}});},{rootMargin:'0px 0px -75% 0px'});
document.querySelectorAll('main h2[id]').forEach(function(h){io.observe(h);});
})();
"""


def _tile(anchor, number, label, warn=False):
    return (
        '<a class="tile%s" href="#%s"><span class="n">%d</span>'
        '<span class="l">%s</span></a>'
        % (" warn" if warn else "", anchor, number, escape(label))
    )


def render_document(doc, source_name, generated_at):
    """Assemble the single self-contained HTML document."""
    phases = doc["phases"]
    reqs = [r for ph in phases for r in ph["requirements"]]
    crits = [c for ph in phases for c in ph["criteria"]]
    labels = LABELS[doc["lang"]]

    toc_items = "".join(
        '<li><a href="#%s">%s</a></li>' % (a, escape(t))
        for lvl, t, a in doc["headings"]
        if lvl == 2
    )

    tiles = []
    if phases:
        # The index table is where a reader compares requirements and criteria;
        # it only exists when there are requirements to list.
        detail = "req-index" if reqs else phases[0]["anchor"]
        tiles.append(_tile(phases[0]["anchor"], len(phases), labels["phases"]))
        tiles.append(_tile(detail, len(reqs), labels["requirements"]))
        tiles.append(_tile(detail, len(crits), labels["criteria"]))
    if doc["non_goals"]:
        tiles.append(_tile("s4", len(doc["non_goals"]), labels["non_goals"]))
    if doc["assumptions"]:
        tiles.append(_tile("assumptions", len(doc["assumptions"]), labels["assumptions"], True))
    dash = '<div class="dash">%s</div>' % "".join(tiles) if tiles else ""

    panel = ""
    if doc["assumptions"]:
        # The line number, not a link: the HTML has no per-line anchors, and the
        # edit belongs in the source markdown anyway.
        items = "".join(
            '<li><span class="rid">L%d</span> %s</li>' % (line_no, render_inline(text))
            for line_no, text in doc["assumptions"]
        )
        panel = (
            '<section class="panel assume" id="assumptions">'
            '<h2>%s (%d)</h2><p>%s</p><ul>%s</ul></section>'
            % (labels["assumptions"], len(doc["assumptions"]), labels["assume_hint"], items)
        )

    index = ""
    if reqs:
        rows = "".join(
            '<tr><td><a href="#%s">%s</a></td><td>%s</td><td>%s</td><td>%d</td></tr>'
            % (
                r["anchor"],
                r["id"],
                escape(ph["title"]),
                render_inline(r["text"]),
                len(ph["criteria"]),
            )
            for ph in phases
            for r in ph["requirements"]
        )
        index = (
            '<section class="panel" id="req-index"><h2>%s</h2>'
            '<div class="scroll"><table>'
            "<tr><th>ID</th><th>%s</th><th>%s</th><th>%s</th></tr>"
            "%s</table></div></section>"
            % (
                labels["index"],
                labels["phase"],
                labels["requirement"],
                labels["criteria_count"],
                rows,
            )
        )

    # Layer 1 of the spec wants a relative link back to the source markdown; the
    # HTML is written as its sibling by default, so the bare name resolves.
    src_link = '<a href="%s">%s</a>' % (escape(source_name), escape(source_name))

    return TEMPLATE % {
        "lang": doc["lang"],
        "title": escape(doc["title"]),
        "style": STYLE,
        "script": SCRIPT,
        "skip": escape(labels["skip"]),
        "source": src_link,
        "generated": escape(generated_at),
        "toc_label": escape(labels["toc"]),
        "toc": toc_items,
        "dash": dash,
        "panel": panel,
        "body": doc["sections_html"],
        "index": index,
        "footer": labels["footer"] % src_link,
    }


LABELS = {
    "ko": {
        "phases": "페이즈", "requirements": "요구사항", "criteria": "수용 기준",
        "non_goals": "Non-Goals", "assumptions": "가정",
        "assume_hint": "아래 항목은 사용자가 확인하지 않은 내용입니다. 검토해 주세요.",
        "index": "요구사항 인덱스", "phase": "페이즈", "requirement": "요구사항",
        "criteria_count": "수용기준 수",
        "toc": "목차", "skip": "본문으로 건너뛰기",
        "footer": "이 문서는 <code>%s</code>에서 생성된 파생물입니다. 수정은 원본 마크다운에서 하세요.",
    },
    "en": {
        "phases": "Phases", "requirements": "Requirements", "criteria": "Acceptance",
        "non_goals": "Non-Goals", "assumptions": "Assumptions",
        "assume_hint": "These items were not confirmed by the user. Please review them.",
        "index": "Requirement index", "phase": "Phase", "requirement": "Requirement",
        "criteria_count": "Criteria",
        "toc": "Contents", "skip": "Skip to content",
        "footer": "Generated from <code>%s</code>. Edit the source markdown, not this file.",
    },
}

TEMPLATE = """<!doctype html>
<html lang="%(lang)s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>%(style)s</style>
</head>
<body>
<a class="skip" href="#main">%(skip)s</a>
<div class="wrap">
<header class="doc">
<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">
<div><h1>%(title)s</h1>
<div class="meta"><span>%(source)s</span><span>%(generated)s</span></div></div>
<button class="toggle" id="themeToggle" type="button">&#9689;</button>
</div>
%(dash)s
</header>
<details class="mtoc"><summary>%(toc_label)s</summary><ol>%(toc)s</ol></details>
<div class="layout">
<nav class="toc" aria-label="%(toc_label)s"><ol>%(toc)s</ol></nav>
<main id="main">
%(panel)s
%(body)s
%(index)s
</main>
</div>
<footer class="doc">%(footer)s</footer>
</div>
<script>%(script)s</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Region 5 of 5: CLI
# --------------------------------------------------------------------------

USAGE = "Usage: python3 prd_to_html.py <path-to-PRD.md> [--output <path.html>]"


def main(argv):
    args = argv[1:]
    out_path = None
    if "--output" in args:
        k = args.index("--output")
        if k + 1 >= len(args):
            print(USAGE, file=sys.stderr)
            return 2
        out_path = Path(args[k + 1])
        args = args[:k] + args[k + 2:]

    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        return 2

    src = Path(args[0])
    if not src.is_file():
        print("Error: file not found: %s" % src, file=sys.stderr)
        return 2
    try:
        text = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("Error: %s is not valid UTF-8 text." % src, file=sys.stderr)
        return 2

    if out_path is None:
        out_path = src.with_suffix(".html")

    doc = parse_document(text, src.stem)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        out_path.write_text(
            render_document(doc, src.name, generated), encoding="utf-8"
        )
    except OSError as exc:
        # A bad --output is a usage error, same contract as a missing input.
        print("Error: cannot write %s: %s" % (out_path, exc), file=sys.stderr)
        return 2
    print("Wrote %s (assumptions: %d)" % (out_path, len(doc["assumptions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
