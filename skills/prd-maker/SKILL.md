---
name: prd-maker
description: Use when the user wants to turn a product/service/tool idea into a PRD (product requirements document) that an AI coding agent can execute — triggers include "PRD 만들어줘", "write a PRD", "기획서 만들어줘", "요구사항 문서", or when the user describes a new product idea and needs a spec before implementation.
---

# PRD Maker

Turn a product idea into a single `PRD.md` that any AI coding agent can execute, through an adaptive interview that works for non-developers and developers alike.

**Announce at start** (in the user's language): "prd-maker 스킬로 PRD를 만들겠습니다."

## Core rules (apply throughout)

- Conduct the interview in the user's language. Write `PRD.md` in that same language.
- One question per message. Never batch questions.
- Prefer multiple-choice questions when the options are enumerable.
- Never re-ask something the user already said.
- If the user says "I don't know", propose one sensible default with a one-line reason and ask only for agreement.
- Anything assumed rather than heard from the user MUST be marked `(가정)` / `(assumption)` in the PRD.
- Keep the total number of interview questions at 10 or fewer. Fill low-priority gaps with marked assumptions instead of asking more.

## Workflow

### Step 0 — Listen
Ask the user to describe what they want to build — any form, any length. If an idea description was already provided (e.g. via command arguments), use it and skip the ask.

### Step 1 — Interview
Read `references/interview-guide.md` and follow it: detect the user's technical level from their first description, then fill the 8-element coverage checklist adaptively, one question at a time.

### Step 2 — Confirm understanding
Summarize everything collected in 3–5 lines. Ask the user to confirm or correct. Do not write the PRD before confirmation.

### Step 3 — Write the PRD
Read `references/prd-template.md` and draft the full PRD following its structure and per-section rules.

### Step 4 — Self-review and deliver
Save the draft as `PRD.md` in the current working directory. Run the structural linter: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/prd-maker/scripts/validate_prd.py PRD.md` — fix any FAIL and re-run (if it still fails after 3 attempts, show the report to the user and ask how to proceed). Then read `references/quality-rules.md` and check the draft against every semantic rule ONCE, fixing violations. In your delivery message, list every `(가정)` item explicitly (the linter's ASSUMPTIONS output helps) and ask the user to review them.

## Edge cases

- **Idea too big** (3+ independent subsystems, e.g. "chat + payments + analytics platform"): detect early, propose narrowing v1 to the single most essential piece. If the user insists on everything, keep the full vision in the Overview but move everything beyond the core into Non-Goals with a "future version" note.
- **Terse answers / user seems fatigued**: don't push. Fill remaining checklist gaps with sensible defaults marked `(가정)` and say clearly that the PRD is assumption-heavy and needs review.
- **`PRD.md` already exists in the current directory**: never overwrite silently. Ask whether to (a) create a new file with a different name or (b) read the existing document and update it with the new interview results.
- **Running inside an existing codebase**: skim for stack signals (package.json, pyproject.toml, go.mod, etc.) and use them as defaults for the Technical Constraints section. On the developer track, confirm the detected stack with the user.
- **User revises an earlier answer**: the newest answer wins. Update silently — do not point out the contradiction.
