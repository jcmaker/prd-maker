# PRD Template

Structure and per-section rules for the output `PRD.md`. Loaded at Step 3 of SKILL.md.

Global rules:
- Write the document in the user's language (the language the interview was conducted in).
- Pure markdown only — no tool-specific syntax (no CLAUDE.md / .cursorrules / AGENTS.md conventions). Any AI coding agent must be able to consume it.
- Every unconfirmed item carries `(가정)` (or `(assumption)` in English documents).

## Document header

Start the PRD with this blockquote, translated into the user's language:

> **For AI agents:** This document is your implementation instruction. Where it is unclear, do not guess — ask the user. When a decision changes during implementation, update this document so it remains the source of truth (living document). Items marked `(가정)` were not confirmed by the user — verify them before relying on them.

## Sections and rules

### 1. Overview
Problem and goal in 2–3 sentences. MUST include the "why" — agents use it to resolve ambiguity on their own.

### 2. Target Users & JTBD
Who, in what situation, trying to accomplish what.

### 3. Core Features (Scope)
One short paragraph per feature. Ordered by priority (checklist element 7).

### 4. Non-Goals
Positive statements only: "이번 버전에서 사용자 인증은 구현하지 않는다." Minimum 3 items — if the interview surfaced fewer, derive plausible scope-creep exclusions from context and mark them `(가정)`. Omission is not a boundary — agents cannot infer scope from silence, so every exclusion must be written down.

### 5. Technical Constraints & Prior Decisions
- Developer-track answers: record as stated.
- Non-developer-track defaults: record WITH the rationale — e.g. "혼자 쓰는 도구이므로 로그인 없이 로컬 저장 — 필요 시 에이전트가 변경 가능 (가정)".
- Data/content (interview checklist element B8): list the kinds of information the product stores or displays, as constraints on the data model — e.g. "기록 항목: 날짜, 거리, 참여자 목록".
- Decisions the agent must not reopen: tag with `[변경 금지]` / `[DO NOT CHANGE]`.

### 6. Phased Requirements
Phase order follows the user's priority answer (checklist element 7). For each phase:
- **Goal**: one sentence.
- **Requirements**: numbered list. Max 50 per phase, aim for ~30 or fewer.
- **Acceptance criteria**: checkbox list (`- [ ]`), every item machine-verifiable (a number, an observable behavior, or a command that can pass/fail).

Phase rules:
- Each phase must end in a runnable, manually verifiable state (no dead ends). Phase 1 alone must produce something that works.
- State dependencies between phases explicitly ("Phase 2 requires Phase 1's storage").

### 7. Success Metrics
Measurable form only. If the user never defined one, derive a modest metric from the problem statement and mark it `(가정)`.

## Skeleton

Use this as the output scaffold (translate headings to the user's language):

```markdown
# [제품 이름] PRD

> **AI 에이전트에게:** 이 문서는 구현 지침입니다. 불명확한 부분은 추측하지 말고
> 사용자에게 질문하세요. 구현 중 결정이 바뀌면 이 문서를 갱신해 source of truth로
> 유지하세요. `(가정)` 표시 항목은 사용자가 확인하지 않은 내용이니, 의존하기
> 전에 사용자에게 확인하세요.

## 1. 개요
[문제와 목표 2~3문장 — "왜" 포함]

## 2. 대상 사용자 & JTBD
[누가, 어떤 상황에서, 무엇을 이루려고]

## 3. 핵심 기능 (스코프)
1. **[기능명]** — [한 문단]
2. ...

## 4. Non-Goals (하지 않는 것)
- 이번 버전에서 [X]는 구현하지 않는다.
- (최소 3개)

## 5. 기술 제약 & 기존 결정
- [결정] — [근거] [필요 시 `[변경 금지]` 또는 `(가정)`]
- 다루는 데이터: [저장/표시할 정보 목록]

## 6. 페이즈별 요구사항

### Phase 1: [이름]
**목표:** [1문장]
**요구사항:**
1. ...
**수용 기준:**
- [ ] [기계 검증 가능한 항목]

### Phase 2: [이름] (Phase 1의 [X] 필요)
...

## 7. 성공 지표
- [측정 가능한 지표] [(가정)]
```
