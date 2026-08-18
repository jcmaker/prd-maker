# prd-to-html Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PRD.md`를 사람이 읽기 위한 단일 self-contained HTML 문서로 변환하는 결정적 파이썬 스크립트와 `/prd-to-html` 커맨드를 추가한다.

**Architecture:** `skills/prd-maker/scripts/prd_to_html.py` 한 파일에 네 구역(파서 / 미니 마크다운 렌더러 / 템플릿 / CLI)을 담는다. 구조 파싱은 기존 `validate_prd.py`의 정규식과 헬퍼를 import해 재사용하므로 린터와 변환기가 같은 것을 "가정"이라 부른다. 출력은 CSS·JS가 인라인된 HTML 파일 하나이며 외부 리소스를 참조하지 않는다.

**Tech Stack:** Python 3 표준 라이브러리만 (`re`, `sys`, `pathlib`, `html.parser`, `unittest`, `datetime`). 새 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-08-18-prd-to-html-design.md`

## Global Constraints

- **stdlib 전용.** 새 서드파티 의존성을 추가하지 않는다. 저장소 전체 정책이다.
- **언어 무관.** 한국어/영어 제목 단어를 절대 매칭하지 않는다. 마크다운 구조(`## N.`, `### `, `- [ ]`, `1. `)와 숫자만 본다.
- **구조 파싱은 fence-stripped 라인, 렌더링은 원본 라인.** 코드 펜스 안의 예시 마크다운이 유령 페이즈나 유령 가정을 만들면 안 된다.
- **출력 HTML에 외부 리소스 0개.** `<script src=`, `<link href=`, `@import`, 외부 URL 리소스 금지.
- **모든 사용자 입력은 이스케이프.** 원문의 raw HTML은 렌더하지 않고 텍스트로 출력한다.
- **종료 코드:** 0 성공 / 2 사용 오류(인자 오류, 파일 없음, UTF-8 아님). `validate_prd.py`의 관례와 동일.
- **UTF-8 강제.** `validate_prd.py`처럼 stdout/stderr을 UTF-8로 reconfigure 한다 (Windows cp1252 대응).
- **ruff `select = ["F", "E9"]` 통과.** `scripts/check-all.sh`가 전부 통과해야 한다.
- **테스트 스타일:** `unittest` + CLI는 `subprocess`. `test_validate_prd.py`의 형태를 따른다.

---

### Task 1: 이스케이프와 인라인 마크다운 렌더러

**Files:**
- Create: `skills/prd-maker/scripts/prd_to_html.py`
- Create: `skills/prd-maker/scripts/test_prd_to_html.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `escape(text) -> str`, `render_inline(text) -> str`, `SAFE_HREF_RE`

- [ ] **Step 1: Write the failing test**

`skills/prd-maker/scripts/test_prd_to_html.py`:

```python
"""Tests for prd_to_html.py — the deterministic PRD-to-HTML converter.

Run with: cd skills/prd-maker/scripts && python3 test_prd_to_html.py
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import prd_to_html as p


class TestEscape(unittest.TestCase):
    def test_escapes_html_metacharacters(self):
        self.assertEqual(p.escape("a & b"), "a &amp; b")
        self.assertEqual(p.escape("<b>"), "&lt;b&gt;")
        self.assertEqual(p.escape('say "hi"'), "say &quot;hi&quot;")

    def test_ampersand_escaped_first(self):
        self.assertEqual(p.escape("<"), "&lt;")


class TestRenderInline(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(p.render_inline("a **b** c"), "a <strong>b</strong> c")

    def test_inline_code(self):
        self.assertEqual(p.render_inline("run `ls -l`"), "run <code>ls -l</code>")

    def test_link_with_safe_scheme(self):
        self.assertEqual(
            p.render_inline("[docs](https://example.com)"),
            '<a href="https://example.com">docs</a>',
        )

    def test_relative_and_anchor_links_allowed(self):
        self.assertIn('href="#s1"', p.render_inline("[a](#s1)"))
        self.assertIn('href="./PRD.md"', p.render_inline("[a](./PRD.md)"))

    def test_javascript_url_is_not_rendered_as_link(self):
        out = p.render_inline("[click](javascript:alert(1))")
        self.assertNotIn("<a ", out)
        self.assertIn("[click]", out)  # left as inert text, not a link

    def test_raw_html_is_escaped_not_rendered(self):
        out = p.render_inline("<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'prd_to_html'`

- [ ] **Step 3: Write minimal implementation**

`skills/prd-maker/scripts/prd_to_html.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: PASS — 8 tests OK

- [ ] **Step 5: Commit**

```bash
git add skills/prd-maker/scripts/prd_to_html.py skills/prd-maker/scripts/test_prd_to_html.py
git commit -m "feat(html): add inline markdown renderer with href allowlist"
```

---

### Task 2: 블록 마크다운 렌더러

**Files:**
- Modify: `skills/prd-maker/scripts/prd_to_html.py` (Region 2 추가)
- Modify: `skills/prd-maker/scripts/test_prd_to_html.py`

**Interfaces:**
- Consumes: `render_inline(text)`, `escape(text)` (Task 1)
- Produces: `slugify(text, used) -> str`, `render_blocks(lines) -> (html_str, headings)` where `headings` is `list[(level:int, text:str, anchor:str)]`

- [ ] **Step 1: Write the failing test**

`test_prd_to_html.py`의 `if __name__` 블록 **위**에 추가:

```python
class TestRenderBlocks(unittest.TestCase):
    def render(self, md):
        html, _ = p.render_blocks(md.splitlines())
        return html

    def test_headings_get_ids(self):
        html, headings = p.render_blocks(["## 1. 개요"])
        self.assertIn("<h2 id=", html)
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0][0], 2)

    def test_duplicate_headings_get_unique_ids(self):
        _, headings = p.render_blocks(["## 개요", "", "## 개요"])
        self.assertNotEqual(headings[0][2], headings[1][2])

    def test_unordered_list(self):
        html = self.render("- a\n- b")
        self.assertIn("<ul>", html)
        self.assertEqual(html.count("<li>"), 2)

    def test_ordered_list(self):
        html = self.render("1. first\n2. second")
        self.assertIn("<ol>", html)

    def test_checkbox_renders_marker_text_not_color_only(self):
        html = self.render("- [ ] 미완료\n- [x] 완료")
        self.assertIn("☐", html)
        self.assertIn("☑", html)

    def test_blockquote(self):
        self.assertIn("<blockquote>", self.render("> 에이전트에게"))

    def test_fenced_code_is_escaped(self):
        html = self.render("```\n<script>x</script>\n```")
        self.assertIn("<pre>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_table(self):
        html = self.render("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<table>", html)
        self.assertIn("<th>", html)
        self.assertIn("<td>", html)

    def test_paragraph(self):
        self.assertIn("<p>", self.render("그냥 문장입니다."))

    def test_unsupported_syntax_survives_as_text(self):
        html = self.render("~~취소선~~")
        self.assertIn("~~취소선~~", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: FAIL — `AttributeError: module 'prd_to_html' has no attribute 'render_blocks'`

- [ ] **Step 3: Write minimal implementation**

`prd_to_html.py`의 Region 1 뒤에 추가:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: PASS — 18 tests OK

- [ ] **Step 5: Commit**

```bash
git add skills/prd-maker/scripts/prd_to_html.py skills/prd-maker/scripts/test_prd_to_html.py
git commit -m "feat(html): add block markdown renderer"
```

---

### Task 3: 구조 파서 (언어·제목·가정·Non-Goals·페이즈)

**Files:**
- Modify: `skills/prd-maker/scripts/prd_to_html.py` (Region 3 앞부분 추가)
- Modify: `skills/prd-maker/scripts/test_prd_to_html.py`

**Interfaces:**
- Consumes: `validate_prd`의 `strip_fenced_blocks`, `find_section_body`, `find_phase_blocks`, `find_assumptions`, `NON_GOAL_ITEM_RE`, `CHECKBOX_RE`, `NUMBERED_ITEM_RE`
- Produces:
  - `detect_lang(text) -> "ko"|"en"`
  - `extract_title(lines, fallback) -> str`
  - `collect_non_goals(stripped_lines) -> list[str]`
  - `collect_phases(stripped_lines) -> list[dict]`, 각 dict는 `{"index": int, "title": str, "anchor": "phase-N", "notes": [str], "requirements": [{"id","anchor","text"}], "criteria": [{"id","anchor","text","checked"}]}`
  - `split_sections(raw_lines) -> list[{"num": int|None, "lines": list[str]}]`

- [ ] **Step 1: Write the failing test**

`test_prd_to_html.py`의 `if __name__` 블록 위에 추가:

```python
SAMPLE_PRD = """# 러닝 크루 PRD

> **AI 에이전트에게:** 이 문서는 구현 지침입니다.

## 1. 개요
동네 러닝 크루의 기록을 남긴다.

## 4. Non-Goals (하지 않는 것)
- 이번 버전에서 결제는 구현하지 않는다.
- 이번 버전에서 소셜 로그인은 구현하지 않는다.
- 이번 버전에서 푸시 알림은 구현하지 않는다. (가정)

## 6. 페이즈별 요구사항

### Phase 1: 기본 동작
**목표:** 기록을 저장한다
**요구사항:**
1. 기록을 입력한다
2. 기록을 저장한다
**수용 기준:**
- [ ] 기록 저장 후 목록에 보인다
- [x] 앱이 실행된다

### Phase 2: 확장 (Phase 1의 저장소 필요)
**목표:** 공유한다
**요구사항:**
1. 링크를 만든다
**수용 기준:**
- [ ] 링크로 기록이 열린다
"""


class TestStructureParsing(unittest.TestCase):
    def stripped(self, text=SAMPLE_PRD):
        from validate_prd import strip_fenced_blocks

        return strip_fenced_blocks(text.splitlines())

    def test_detect_lang_korean(self):
        self.assertEqual(p.detect_lang("한국어 문서입니다"), "ko")

    def test_detect_lang_english(self):
        self.assertEqual(p.detect_lang("This is an English PRD"), "en")

    def test_extract_title(self):
        self.assertEqual(
            p.extract_title(SAMPLE_PRD.splitlines(), "PRD"), "러닝 크루 PRD"
        )

    def test_extract_title_falls_back(self):
        self.assertEqual(p.extract_title(["본문뿐"], "PRD"), "PRD")

    def test_collect_non_goals(self):
        goals = p.collect_non_goals(self.stripped())
        self.assertEqual(len(goals), 3)
        self.assertIn("결제", goals[0])

    def test_collect_phases_counts(self):
        phases = p.collect_phases(self.stripped())
        self.assertEqual(len(phases), 2)
        self.assertEqual(len(phases[0]["requirements"]), 2)
        self.assertEqual(len(phases[0]["criteria"]), 2)

    def test_requirement_ids(self):
        phases = p.collect_phases(self.stripped())
        self.assertEqual(phases[0]["requirements"][1]["id"], "P1-R2")
        self.assertEqual(phases[1]["requirements"][0]["anchor"], "p2-r1")

    def test_criteria_ids_and_checked_state(self):
        crits = p.collect_phases(self.stripped())[0]["criteria"]
        self.assertEqual(crits[0]["id"], "P1-A1")
        self.assertFalse(crits[0]["checked"])
        self.assertTrue(crits[1]["checked"])

    def test_phase_notes_captured(self):
        notes = p.collect_phases(self.stripped())[0]["notes"]
        self.assertTrue(any("목표" in x for x in notes))

    def test_fenced_examples_do_not_create_phantom_phases(self):
        text = "## 6. 요구사항\n\n```\n### Phase 9: 가짜\n- [ ] 가짜 기준\n```\n"
        self.assertEqual(p.collect_phases(self.stripped(text)), [])

    def test_split_sections(self):
        chunks = p.split_sections(SAMPLE_PRD.splitlines())
        nums = [c["num"] for c in chunks]
        self.assertEqual(nums[0], None)
        self.assertIn(1, nums)
        self.assertIn(6, nums)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: FAIL — `AttributeError: module 'prd_to_html' has no attribute 'detect_lang'`

- [ ] **Step 3: Write minimal implementation**

`prd_to_html.py`의 상단 import 구역에 추가:

```python
from validate_prd import (
    CHECKBOX_RE,
    NON_GOAL_ITEM_RE,
    NUMBERED_ITEM_RE,
    find_assumptions,
    find_phase_blocks,
    find_section_body,
    strip_fenced_blocks,
)
```

Region 2 뒤에 추가:

```python
# --------------------------------------------------------------------------
# Region 3 of 4: structure parsing (reuses validate_prd's regexes)
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

    Phase-internal order is normalized to notes -> requirements -> criteria,
    which is the order the PRD template already writes them in.
    """
    body = find_section_body(stripped_lines, 6)
    if body is None:
        return []
    phases = []
    for index, (title, block) in enumerate(find_phase_blocks(body), start=1):
        notes, reqs, crits = [], [], []
        for _, text in block:
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
                        "text": NUMBER_PREFIX_RE.sub("", content).strip(),
                    }
                )
            else:
                notes.append(content)
        phases.append(
            {
                "index": index,
                "title": title,
                "anchor": "phase-%d" % index,
                "notes": notes,
                "requirements": reqs,
                "criteria": crits,
            }
        )
    return phases


def split_sections(raw_lines):
    """Split raw lines at every `## ` heading. The preamble chunk has num=None."""
    chunks = [{"num": None, "lines": []}]
    in_fence = False
    fence = None
    for line in raw_lines:
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
            chunks.append({"num": num, "lines": [line]})
        else:
            chunks[-1]["lines"].append(line)
    return [c for c in chunks if any(x.strip() for x in c["lines"])]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: PASS — 30 tests OK

- [ ] **Step 5: Commit**

```bash
git add skills/prd-maker/scripts/prd_to_html.py skills/prd-maker/scripts/test_prd_to_html.py
git commit -m "feat(html): parse PRD structure by reusing validate_prd helpers"
```

---

### Task 4: HTML 템플릿 조립

**Files:**
- Modify: `skills/prd-maker/scripts/prd_to_html.py` (Region 3 나머지 + STYLE/SCRIPT 상수)
- Modify: `skills/prd-maker/scripts/test_prd_to_html.py`

**Interfaces:**
- Consumes: Task 1–3의 모든 함수
- Produces: `parse_document(text, fallback_title) -> dict`, `render_document(doc, source_name, generated_at) -> str`, 상수 `STYLE`, `SCRIPT`

`parse_document`가 돌려주는 dict의 키: `title`, `lang`, `headings`, `assumptions`, `non_goals`, `phases`, `sections_html`(문자열).

- [ ] **Step 1: Write the failing test**

`test_prd_to_html.py`의 `if __name__` 블록 위에 추가:

```python
class TestDocumentAssembly(unittest.TestCase):
    def build(self, text=SAMPLE_PRD):
        doc = p.parse_document(text, "PRD")
        return p.render_document(doc, "PRD.md", "2026-08-18 12:00")

    def test_has_lang_attribute(self):
        self.assertIn('<html lang="ko"', self.build())

    def test_title_ignores_headings_inside_code_fences(self):
        doc = p.parse_document("```\n# 예시 제목\n```\n\n# 진짜 제목\n", "PRD")
        self.assertEqual(doc["title"], "진짜 제목")

    def test_dashboard_has_one_tile_per_metric(self):
        html = self.build()
        self.assertIn('class="dash"', html)
        # phases, requirements, criteria, non-goals, assumptions
        self.assertEqual(html.count('class="tile'), 5)

    def test_assumption_panel_lists_every_assumption(self):
        doc = p.parse_document(SAMPLE_PRD, "PRD")
        html = p.render_document(doc, "PRD.md", "t")
        self.assertEqual(len(doc["assumptions"]), 1)
        self.assertIn('id="assumptions"', html)
        panel = html.split('id="assumptions"', 1)[1].split("</section>", 1)[0]
        self.assertIn("푸시 알림", panel)

    def test_assumption_panel_absent_when_no_assumptions(self):
        doc = p.parse_document("# 메모\n\n확인되지 않은 내용 없음.\n", "메모")
        self.assertEqual(doc["assumptions"], [])
        self.assertNotIn('id="assumptions"', p.render_document(doc, "memo.md", "t"))

    def test_requirement_anchors_exist(self):
        html = self.build()
        self.assertIn('id="p1-r1"', html)
        self.assertIn('id="p1-a1"', html)

    def test_requirement_index_table_present(self):
        self.assertIn("req-index", self.build())

    def test_footer_states_derived_status(self):
        self.assertIn("PRD.md", self.build())

    def test_print_and_dark_css_present(self):
        html = self.build()
        self.assertIn("@media print", html)
        self.assertIn("prefers-color-scheme", html)

    def test_korean_typography_rules_present(self):
        self.assertIn("keep-all", self.build())

    def test_no_external_resources(self):
        html = self.build()
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link href=", html)
        self.assertNotIn("@import", html)

    def test_partial_enhancement_drops_missing_pieces(self):
        html = p.render_document(
            p.parse_document("# 그냥 메모\n\n본문 한 줄.\n", "메모"), "memo.md", "t"
        )
        self.assertIn("그냥 메모", html)
        self.assertNotIn("req-index", html)
        self.assertNotIn('id="p1-r1"', html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: FAIL — `AttributeError: module 'prd_to_html' has no attribute 'parse_document'`

- [ ] **Step 3: Write minimal implementation**

Region 3 끝에 추가:

```python
def parse_document(text, fallback_title):
    raw = text.splitlines()
    stripped = strip_fenced_blocks(raw)
    phases = collect_phases(stripped)

    used_slugs = set()
    headings, parts = [], []
    for chunk in split_sections(raw):
        num = chunk["num"]
        if num == 6 and phases:
            html, hs = render_phase_section(chunk["lines"], phases, used_slugs)
        else:
            html, hs = render_blocks(chunk["lines"], used_slugs)
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


def render_phase_section(chunk_lines, phases, used_slugs):
    """Render section 6 as phase cards so requirements get stable anchors."""
    heading = chunk_lines[0].strip() if chunk_lines else "## 6."
    head_html, headings = render_blocks([heading], used_slugs)
    out = [head_html, '<ol class="tl">']
    for ph in phases:
        used_slugs.add(ph["anchor"])
        headings.append((3, ph["title"], ph["anchor"]))
        out.append('<li class="phase"><h3 id="%s">%s</h3>' % (ph["anchor"], escape(ph["title"])))
        for note in ph["notes"]:
            out.append("<p>" + render_inline(note) + "</p>")
        if ph["requirements"]:
            out.append("<ol>")
            for r in ph["requirements"]:
                out.append(
                    '<li id="%s"><span class="rid">%s</span> %s</li>'
                    % (r["anchor"], r["id"], render_inline(r["text"]))
                )
            out.append("</ol>")
        if ph["criteria"]:
            out.append('<ul class="crit">')
            for c in ph["criteria"]:
                out.append(
                    '<li id="%s" class="%s"><span class="mark">%s</span>'
                    '<span class="rid">%s</span> %s</li>'
                    % (
                        c["anchor"],
                        "done" if c["checked"] else "todo",
                        "☑" if c["checked"] else "☐",
                        c["id"],
                        render_inline(c["text"]),
                    )
                )
            out.append("</ul>")
        out.append("</li>")
    out.append("</ol>")
    return "\n".join(out), headings
```

그다음 Region 4 앞에 STYLE/SCRIPT 상수와 `render_document`를 추가:

```python
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
        tiles.append(_tile(phases[0]["anchor"], len(phases), labels["phases"]))
        tiles.append(_tile(phases[0]["anchor"], len(reqs), labels["requirements"]))
        tiles.append(_tile(phases[0]["anchor"], len(crits), labels["criteria"]))
    if doc["non_goals"]:
        tiles.append(_tile("s4", len(doc["non_goals"]), labels["non_goals"]))
    if doc["assumptions"]:
        tiles.append(_tile("assumptions", len(doc["assumptions"]), labels["assumptions"], True))
    dash = '<div class="dash">%s</div>' % "".join(tiles) if tiles else ""

    panel = ""
    if doc["assumptions"]:
        items = "".join(
            "<li>%s</li>" % render_inline(text) for _, text in doc["assumptions"]
        )
        panel = (
            '<section class="panel assume" id="assumptions">'
            '<h2>%s (%d)</h2><p>%s</p><ul>%s</ul></section>'
            % (labels["assumptions"], len(doc["assumptions"]), labels["assume_hint"], items)
        )

    index = ""
    if reqs:
        rows = "".join(
            '<tr><td><a href="#%s">%s</a></td><td>%s</td><td>%s</td></tr>'
            % (r["anchor"], r["id"], escape(ph["title"]), render_inline(r["text"]))
            for ph in phases
            for r in ph["requirements"]
        )
        index = (
            '<section class="panel" id="req-index"><h2>%s</h2>'
            '<div class="scroll"><table><tr><th>ID</th><th>%s</th><th>%s</th></tr>'
            "%s</table></div></section>"
            % (labels["index"], labels["phase"], labels["requirement"], rows)
        )

    return TEMPLATE % {
        "lang": doc["lang"],
        "title": escape(doc["title"]),
        "style": STYLE,
        "script": SCRIPT,
        "skip": escape(labels["skip"]),
        "source": escape(source_name),
        "generated": escape(generated_at),
        "toc_label": escape(labels["toc"]),
        "toc": toc_items,
        "dash": dash,
        "panel": panel,
        "body": doc["sections_html"],
        "index": index,
        "footer": labels["footer"] % escape(source_name),
    }


LABELS = {
    "ko": {
        "phases": "페이즈", "requirements": "요구사항", "criteria": "수용 기준",
        "non_goals": "Non-Goals", "assumptions": "가정",
        "assume_hint": "아래 항목은 사용자가 확인하지 않은 내용입니다. 검토해 주세요.",
        "index": "요구사항 인덱스", "phase": "페이즈", "requirement": "요구사항",
        "toc": "목차", "skip": "본문으로 건너뛰기",
        "footer": "이 문서는 <code>%s</code>에서 생성된 파생물입니다. 수정은 원본 마크다운에서 하세요.",
    },
    "en": {
        "phases": "Phases", "requirements": "Requirements", "criteria": "Acceptance",
        "non_goals": "Non-Goals", "assumptions": "Assumptions",
        "assume_hint": "These items were not confirmed by the user. Please review them.",
        "index": "Requirement index", "phase": "Phase", "requirement": "Requirement",
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: PASS — 40 tests OK

- [ ] **Step 5: Commit**

```bash
git add skills/prd-maker/scripts/prd_to_html.py skills/prd-maker/scripts/test_prd_to_html.py
git commit -m "feat(html): assemble self-contained HTML document template"
```

---

### Task 5: CLI와 통합 검증

**Files:**
- Modify: `skills/prd-maker/scripts/prd_to_html.py` (Region 4)
- Modify: `skills/prd-maker/scripts/test_prd_to_html.py`

**Interfaces:**
- Consumes: `parse_document`, `render_document`
- Produces: `main(argv) -> int`, CLI 진입점

- [ ] **Step 1: Write the failing test**

`test_prd_to_html.py` 상단 import에 `import subprocess`, `import tempfile`을 추가하고, `if __name__` 블록 위에 추가:

```python
SCRIPT_PATH = pathlib.Path(__file__).parent / "prd_to_html.py"
EXAMPLES = pathlib.Path(__file__).resolve().parents[3] / "docs" / "examples"


def run_cli(args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)] + args,
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode, result.stdout + result.stderr


class TestCLI(unittest.TestCase):
    def write_tmp(self, text, suffix=".md"):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        )
        f.write(text)
        f.close()
        self.addCleanup(lambda: pathlib.Path(f.name).unlink(missing_ok=True))
        return pathlib.Path(f.name)

    def test_writes_sibling_html_file(self):
        src = self.write_tmp(SAMPLE_PRD)
        code, out = run_cli([str(src)])
        self.assertEqual(code, 0, out)
        target = src.with_suffix(".html")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.assertTrue(target.is_file())

    def test_output_flag(self):
        src = self.write_tmp(SAMPLE_PRD)
        dest = pathlib.Path(tempfile.gettempdir()) / "prd_to_html_out.html"
        self.addCleanup(lambda: dest.unlink(missing_ok=True))
        code, out = run_cli([str(src), "--output", str(dest)])
        self.assertEqual(code, 0, out)
        self.assertIn("러닝 크루", dest.read_text(encoding="utf-8"))

    def test_missing_argument_exits_2(self):
        code, out = run_cli([])
        self.assertEqual(code, 2)
        self.assertIn("Usage", out)

    def test_missing_file_exits_2(self):
        self.assertEqual(run_cli(["/no/such/PRD.md"])[0], 2)

    def test_non_utf8_exits_2(self):
        f = tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False)
        f.write("# 제목\n".encode("euc-kr"))
        f.close()
        self.addCleanup(lambda: pathlib.Path(f.name).unlink(missing_ok=True))
        code, out = run_cli([f.name])
        self.assertEqual(code, 2)
        self.assertIn("UTF-8", out)

    def test_empty_file_still_produces_html(self):
        src = self.write_tmp("")
        target = src.with_suffix(".html")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.assertEqual(run_cli([str(src)])[0], 0)
        self.assertIn("<html", target.read_text(encoding="utf-8"))


class TagBalance(HTMLParser):
    """Fails on unbalanced or mis-nested tags.

    `HTMLParser` alone accepts almost anything — it recovers silently from
    unclosed and mismatched tags — so feeding it the output only proves the
    generator did not raise. This subclass tracks the open-tag stack, which is
    what "well-formed" in spec section 7 actually means.
    """

    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append("</%s> with nothing open" % tag)
        elif self.stack[-1] != tag:
            self.errors.append("expected </%s>, got </%s>" % (self.stack[-1], tag))
        else:
            self.stack.pop()


class TestSpecAcceptance(unittest.TestCase):
    """The six checks named in section 7 of the design spec."""

    def convert(self, path):
        text = pathlib.Path(path).read_text(encoding="utf-8")
        doc = p.parse_document(text, pathlib.Path(path).stem)
        return doc, p.render_document(doc, pathlib.Path(path).name, "t")

    def test_1_examples_are_well_formed(self):
        files = sorted(EXAMPLES.glob("*.md"))
        self.assertTrue(files, "docs/examples/*.md not found")
        for f in files:
            _, html = self.convert(f)
            checker = TagBalance()
            checker.feed(html)
            checker.close()
            self.assertEqual(checker.errors, [], f.name)
            self.assertEqual(checker.stack, [], "%s: unclosed %s" % (f.name, checker.stack))

    def test_2_self_contained(self):
        for f in sorted(EXAMPLES.glob("*.md")):
            _, html = self.convert(f)
            self.assertNotIn("<script src=", html)
            self.assertNotIn("<link href=", html)
            self.assertNotIn("@import", html)
            self.assertNotIn('src="http', html)

    def test_3_assumption_count_matches_linter(self):
        from validate_prd import find_assumptions, strip_fenced_blocks

        for f in sorted(EXAMPLES.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            expected = len(find_assumptions(strip_fenced_blocks(text.splitlines())))
            doc, _ = self.convert(f)
            self.assertEqual(len(doc["assumptions"]), expected, f.name)

    def test_4_script_input_is_neutralized(self):
        doc = p.parse_document("# T\n\n<script>alert(1)</script>\n", "T")
        html = p.render_document(doc, "T.md", "t")
        body = html.split("<main", 1)[1]
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_5_arbitrary_markdown_converts(self):
        doc = p.parse_document("# 회의록\n\n- 항목 하나\n- 항목 둘\n", "회의록")
        html = p.render_document(doc, "notes.md", "t")
        self.assertIn("회의록", html)
        # the body must survive, not just the title
        self.assertIn("항목 하나", html)
        self.assertIn("항목 둘", html)
        self.assertNotIn("req-index", html)

    def test_6_print_and_dark_css(self):
        _, html = self.convert(sorted(EXAMPLES.glob("*.md"))[0])
        self.assertIn("@media print", html)
        self.assertIn("prefers-color-scheme", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: FAIL — CLI 테스트가 exit code 1과 `Usage`가 아닌 traceback을 낸다 (`main`이 없음)

- [ ] **Step 3: Write minimal implementation**

`prd_to_html.py` 맨 끝에 추가:

```python
# --------------------------------------------------------------------------
# Region 4 of 4: CLI
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
    out_path.write_text(
        render_document(doc, src.name, generated), encoding="utf-8"
    )
    print("Wrote %s (assumptions: %d)" % (out_path, len(doc["assumptions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

파일 상단 import 구역에 추가:

```python
from datetime import datetime
from pathlib import Path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/prd-maker/scripts && python3 test_prd_to_html.py`
Expected: PASS — 52 tests OK

수동 확인: `python3 skills/prd-maker/scripts/prd_to_html.py docs/examples/bookmark-saas.md --output /tmp/check.html` 후 브라우저에서 열어 목차·대시보드·다크 토글·`Cmd+P` 인쇄 미리보기를 확인한다.

- [ ] **Step 5: Commit**

```bash
git add skills/prd-maker/scripts/prd_to_html.py skills/prd-maker/scripts/test_prd_to_html.py
git commit -m "feat(html): add CLI and spec acceptance tests"
```

---

### Task 6: 커맨드·스킬 연결·CI

**Files:**
- Create: `commands/prd-to-html.md`
- Modify: `skills/prd-maker/references/quality-rules.md` (Delivery message requirements)
- Modify: `.github/workflows/ci.yml` (`linter-tests` 잡)
- Modify: `scripts/check-all.sh`
- Modify: `README.md`, `README.ko.md` (구조 트리와 사용법)

**Interfaces:**
- Consumes: `prd_to_html.py` CLI (Task 5)
- Produces: `/prd-to-html` 커맨드

- [ ] **Step 1: 커맨드 파일 생성**

`commands/prd-to-html.md`:

```markdown
---
description: PRD.md를 사람이 읽기 좋은 단일 HTML 문서로 변환합니다
---

Run the deterministic converter on the target markdown file and report where the
HTML was written.

Target file: `$ARGUMENTS` — if empty, use `PRD.md` in the current working directory.

Run:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/prd-maker/scripts/prd_to_html.py <target>

(Other agents: the script lives in this plugin's `skills/prd-maker/scripts/` directory.)

If the target file does not exist, say so and stop — do not invent a PRD.

After it succeeds, tell the user the output path, note that the HTML is a derived
view of the markdown (edits belong in the source file), and mention the assumption
count the script reported if it is greater than zero.
```

- [ ] **Step 2: quality-rules.md에 연결 추가**

`skills/prd-maker/references/quality-rules.md`의 "Delivery message requirements" 목록 맨 끝(현재 4번 항목 뒤)에 추가:

```markdown
5. Offer the human-readable HTML view — the PRD is written for coding agents, but the
   project owner has to understand it too. Ask whether to generate it; only run
   `python3 <this-skill-dir>/scripts/prd_to_html.py PRD.md` if the user agrees. The
   HTML is a derived view, never a second source of truth.
```

- [ ] **Step 3: CI와 로컬 체크에 테스트 추가**

`.github/workflows/ci.yml`의 `linter-tests` 잡에서 "Run validate_prd.py test suite" 스텝 **뒤**에 추가:

```yaml
      - name: Run prd_to_html.py test suite
        run: python3 skills/prd-maker/scripts/test_prd_to_html.py
```

`scripts/check-all.sh`에서 `python3 skills/prd-maker/scripts/test_validate_prd.py` 줄 **뒤**에 추가:

```sh
python3 skills/prd-maker/scripts/test_prd_to_html.py
```

- [ ] **Step 4: 전체 검증 실행**

Run: `sh scripts/check-all.sh`
Expected: 모든 테스트 PASS, `check_skill_structure.py`·`check_manifests.py` PASS, ruff 통과

Run: `python3 skills/prd-maker/scripts/prd_to_html.py docs/examples/consumer-app.md --output /tmp/consumer.html`
Expected: `Wrote /tmp/consumer.html (assumptions: N)` — 종료 코드 0

- [ ] **Step 5: README 갱신**

`README.md`의 구조 트리(108행 부근)에서 `commands/prd-maker.md` 줄 아래에 추가:

```
├── commands/prd-to-html.md        # /prd-to-html slash command (Claude Code)
```

그리고 `skills/prd-maker/scripts/validate_prd.py`를 설명하는 근처(181행 부근)에 한 문단 추가:

```markdown
### Reading the PRD as a human

`PRD.md` is written for coding agents. To read it yourself — or to hand it to a
stakeholder — convert it to a single self-contained HTML file:

    python3 skills/prd-maker/scripts/prd_to_html.py PRD.md

The HTML is a derived view: it never adds a fact that is not in the markdown, and
it can be regenerated or deleted at any time. Edit `PRD.md`, not the HTML.
```

`README.ko.md`의 대응 위치에도 같은 내용을 한국어로 추가한다.

- [ ] **Step 6: Commit**

```bash
git add commands/prd-to-html.md skills/prd-maker/references/quality-rules.md \
        .github/workflows/ci.yml scripts/check-all.sh README.md README.ko.md
git commit -m "feat(html): add /prd-to-html command, skill hook, and CI gate"
```

---

## 완료 기준

- `sh scripts/check-all.sh` 전부 통과
- `docs/examples/*.md` 두 파일이 변환되고 브라우저에서 열림
- `/prd-to-html`이 슬래시 커맨드 목록에 나타남
- 스펙 §7의 검증 6종이 테스트로 존재하고 통과
