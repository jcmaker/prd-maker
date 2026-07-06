---
description: 아이디어를 인터뷰해서 AI 에이전트가 실행할 수 있는 PRD.md를 만듭니다
---

Invoke the prd-maker skill via the Skill tool to interview the user about their product idea and generate PRD.md. Only if the Skill tool is unavailable, read ${CLAUDE_PLUGIN_ROOT}/skills/prd-maker/SKILL.md and follow it directly.

If arguments were provided, treat them as the user's initial idea description and skip Step 0's ask: $ARGUMENTS
