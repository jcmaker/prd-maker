# Quality Rules — pre-delivery self-review

Loaded at Step 4 of SKILL.md. Run this checklist ONCE against the PRD draft. Fix every violation you find, then deliver. No recursive re-review.

Structural checks (section presence/order, non-goals ≥ 3, phase checkboxes, ≤ 50 requirements per phase) are automated by `scripts/validate_prd.py`, which SKILL.md Step 4 runs first — this checklist covers the semantic judgments a script cannot make.

| # | Check | Fail example → Fix |
|---|---|---|
| 1 | Every acceptance criterion is machine-verifiable (a number, an observable behavior, or a pass/fail command) | "빠르게 로딩된다" → "첫 화면이 3초 이내에 표시된다" |
| 2 | Non-goals are positive statements, at least 3 items, and cover the likely scope-creep risks of this product | 멀티유저 앱인데 인증 관련 non-goal 없음 → "이번 버전에서 소셜 로그인은 구현하지 않는다" 추가 |
| 3 | Phase 1 alone produces something runnable and manually verifiable | Phase 1이 "DB 설계만" → 눈에 보이는 동작 하나를 Phase 1로 이동 |
| 4 | No adjective/adverb-only requirements remain | "직관적인 UI" → "모든 핵심 기능이 2클릭 이내로 도달 가능" |
| 5 | Nothing was invented: every item the user did not confirm carries `(가정)`, and derived tech defaults carry a rationale | 조용히 선택된 스택 → 근거 병기 + `(가정)` 표시 |

## Delivery message requirements

After saving `PRD.md`, the message to the user MUST:
1. List every `(가정)` item as a bullet list and ask the user to confirm or correct them.
2. Remind the user the PRD is a living document: "구현 중 결정이 바뀌면 이 문서를 갱신하세요."
3. Suggest the natural next step: hand `PRD.md` to an AI coding agent (e.g. a fresh Claude Code session) with "이 PRD대로 구현해줘".
4. If the user then confirms or corrects any `(가정)` item, update `PRD.md` accordingly and remove the confirmed marks — otherwise the implementing agent will re-verify them with the user before starting.
