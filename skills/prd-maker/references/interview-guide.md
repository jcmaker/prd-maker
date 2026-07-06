# Interview Guide

How to run the adaptive interview. Loaded at Step 1 of SKILL.md. All questions below are examples — phrase them naturally in the user's language.

## A. Detect the technical level (no explicit quiz)

Infer from the user's first description:

- **Developer track** — mentions technologies, stacks, APIs, databases, repos ("React로 만들려고", "crawl an API", "Postgres에 저장").
- **Non-developer track** — describes outcomes in product words only ("앱 같은 거", "a site where people can sign up").
- **Ambiguous** — ask exactly one light question: "평소에 직접 코드를 작성하시나요?" / "Do you usually write code yourself?"

The track changes WHAT YOU ASK, never what the PRD must contain. Each table topic feeds a checklist element in B (noted in parentheses) — an answer here fills that element, so never re-ask it:

| Topic (fills element) | Developer track | Non-developer track |
|---|---|---|
| Stack (→ B6) | Ask preference directly | Do NOT ask. Derive a sensible default from product answers; record it in the PRD with rationale |
| Platform (→ B6) | "웹/모바일/CLI 중 어디에?" | "주로 폰에서 쓰나요, 컴퓨터에서 쓰나요?" |
| Users/auth (→ B2, B6) | "인증이 필요한가요? 방식은?" | "혼자 쓰나요, 여러 명이 같이 쓰나요?" |
| Data (→ B8) | "저장소나 스키마 생각이 있으세요?" | "어떤 정보를 기록하거나 보여줘야 하나요?" |

## B. Coverage checklist — the 8 required elements

First, extract everything the user's initial description already answers. Then ask ONLY about empty elements, one at a time, in this priority order:

1. **Problem** (why build this) — "이걸 만들면 어떤 불편이 사라지나요?"
2. **Target user** (who uses it) — "누가 쓰게 되나요? 본인용인가요, 다른 사람들도 쓰나요?"
3. **Core features, 3–7** (what it does) — "꼭 있어야 하는 기능을 꼽는다면 어떤 것들인가요?"
4. **Non-goals** — users rarely volunteer these. Propose plausible candidates from context and confirm: "혹시 [결제/로그인/알림]은 이번 범위에서 빼는 게 맞을까요?"
5. **Success criteria** — "뭐가 되면 '됐다'고 느끼실까요?"
6. **Technical constraints / prior decisions** — depth per track (see A)
7. **Priority** — "이 중 딱 하나부터 동작해야 한다면 뭐부터인가요?" (this becomes the phase order)
8. **Data/content** — what information the product handles

## C. Question strategy

- One question per message. Multiple choice when the options are enumerable.
- "모르겠어요" → give ONE recommendation with a one-line reason, ask yes/no. Never present a second open-ended question about the same element. If the user rejects the recommendation, ask what they'd prefer instead (counts toward the cap); if they still can't decide, record your recommendation marked `(가정)` and move on.
- Hard cap: 10 questions total (including the level-check question). When near the cap, stop asking; fill the remaining elements (usually 5 and 8) with sensible defaults marked `(가정)`.
- Watch for the "idea too big" signal (3+ independent subsystems) from the very first description — trigger the narrowing edge case in SKILL.md immediately, BEFORE spending questions on details.

## D. Exit condition

All 8 elements are filled (by answer or by marked assumption) → summarize in 3–5 lines → user confirms → proceed to PRD writing (SKILL.md Step 3).
