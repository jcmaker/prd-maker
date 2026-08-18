---
description: PRD.md를 사람이 읽기 좋은 단일 HTML 문서로 변환합니다
---

Invoke the prd-to-html skill via the Skill tool to convert a markdown document into a single self-contained HTML page. Only if the Skill tool is unavailable, read ${CLAUDE_PLUGIN_ROOT}/skills/prd-to-html/SKILL.md and follow it directly.

If arguments were provided, treat them as the target file path; otherwise the skill uses `PRD.md` in the current working directory: $ARGUMENTS
