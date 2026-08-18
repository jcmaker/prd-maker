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
