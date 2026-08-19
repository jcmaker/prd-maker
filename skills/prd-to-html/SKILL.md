---
name: prd-to-html
description: Use when the user wants to read an existing PRD or markdown spec as a human-readable HTML page, or hand one to a stakeholder — triggers include "PRD를 HTML로", "PRD 읽기 좋게 만들어줘", "기획서 HTML로 변환", "convert this PRD to HTML", "make my PRD readable", "PRD를 사람이 읽게". This renders a document that already exists; use prd-maker instead when the user still needs the PRD written.
---

# PRD to HTML

Convert an existing markdown document into a single self-contained HTML page a human can actually read.

**Announce at start** (in the user's language): "prd-to-html 스킬로 HTML 뷰를 만들겠습니다."

## What this is for

`PRD.md` is written for coding agents. The project owner has to understand the same document — what is being built, what is deliberately excluded, and which `(가정)` / `(assumption)` items they still need to confirm. This skill renders that view.

The converter is a deterministic script, not a judgment call. Your job is to pick the right target file, run it, and report the result accurately. Do not write HTML yourself, and do not edit the output.

## Workflow

### Step 1 — Pick the target

Use the file the user named. If they named none, use `PRD.md` in the current working directory.

If the target does not exist, say so and stop. Never invent a PRD, and never fall back to a different file without asking.

### Step 2 — Run the converter

```
python3 <converter> <target>
```

The converter is `../prd-maker/scripts/prd_to_html.py`, relative to this skill's own directory. In Claude Code that resolves to `${CLAUDE_PLUGIN_ROOT}/skills/prd-maker/scripts/prd_to_html.py`; other agents expose it as a sibling of the folder this SKILL.md was loaded from. It needs only Python 3 — no dependencies to install.

It writes `<target>.html` beside the source. Pass `--output <path>` when the user wants it elsewhere. It prints the output path and the number of `(가정)` / `(assumption)` items it found.

Exit code 2 means a usage error — a missing file, a bad argument, or a file that is not valid UTF-8. Report what it says rather than retrying with different arguments.

### Step 3 — Report

Tell the user:
1. Where the HTML was written.
2. The assumption count, if it is greater than zero — those are the items the owner still needs to confirm, and the HTML lists each one with its source line.
3. That the HTML is a **derived view**: it contains nothing that is not in the markdown, and edits belong in the source file. Regenerate it after changing the markdown; never hand-edit the HTML.

## Edge cases

- **The document is not a PRD.** It still converts. Each part of the summary dashboard appears only when its data exists, so an arbitrary markdown file becomes a plain readable page rather than an error. Say plainly that the PRD-specific sections are absent because the document has no phases or non-goals.
- **The HTML already exists.** Overwriting is correct and needs no confirmation — the file is a regenerable derivative, unlike `PRD.md`.
- **The user asks for a change to the HTML** (different colors, an extra section, a diagram): the converter takes no styling options. Explain that the output is fixed by design, and that content changes belong in the markdown, which regenerating will pick up.
- **The user wants a PDF.** Open the HTML in a browser and print to PDF. It carries print styles for exactly this.
