# Habit Tracker Consumer App PRD

> **For AI agents:** This document is your implementation instruction. Where it is unclear, do not guess — ask the user. When a decision changes during implementation, update this document so it remains the source of truth (living document). Items marked `(assumption)` were not confirmed by the user — verify them before relying on them.

## 1. Overview
Building positive daily habits is difficult when tracking apps are overly complicated and require complex setup. This product provides a simple mobile-friendly web app where users can create up to 5 daily habits and log completions with a single tap. The goal is to maximize daily consistency through zero-friction habit logging.

## 2. Target Users & JTBD
- **Target Users:** Busy individuals wanting to build 2-3 healthy daily routines (e.g. drinking water, reading, stretching).
- **Jobs to Be Done:** When completing a daily task, users want to check off the item in under 2 seconds without navigating complicated menus or entering numbers.

## 3. Core Features (Scope)
1. **Daily Checklist View** — Clean interface showing active daily habits with large touch targets.
2. **Streak Tracking** — Automatic streak counter for consecutive days completed.
3. **Local Data Persistence** — Instant offline-first habit storage without mandatory account sign-up.

## 4. Non-Goals
- Social sharing and leaderboards are not implemented in this version.
- Complex numeric habit tracking (e.g. counting exact milliliters of water) is not implemented in this version.
- Push notifications via native mobile device services are not implemented in this version. (assumption)

## 5. Technical Constraints & Prior Decisions
- Single-page web application using standard React and Tailwind CSS — rationale: non-developer personal utility tool with quick deployment (assumption)
- Storage: Browser LocalStorage and IndexedDB — rationale: single-user device tracking without server complexity (assumption)
- Authentication: No login required for v1 — rationale: immediate onboarding with zero sign-up friction (assumption)
- Managed Data: Habit name, icon, target days per week, completion timestamps, current streak count

## 6. Phased Requirements

### Phase 1: Local Habit Logging and Streaks
**Goal:** Users can add habits and toggle daily completion status with local persistence.
**Requirements:**
1. Render today's habit checklist with complete/incomplete state.
2. Allow adding and deleting custom habit names (max 5 active habits).
3. Persist check-in history to LocalStorage.
**Acceptance criteria:**
- [ ] Tapping a habit checkbox marks it completed and persists state across page reloads.
- [ ] Streak count increments by +1 when completed on consecutive calendar days.
- [ ] Users can delete or rename habits from an edit modal.

### Phase 2: Weekly Progress Summary
**Goal:** Display a visual weekly completion grid to motivate continued streaks.
**Requirements:**
1. Render a 7-day completion dot matrix for each active habit.
2. Calculate weekly completion percentage.
**Acceptance criteria:**
- [ ] Grid accurately reflects completion dots for Monday through Sunday.
- [ ] Summary calculates total check-in rate for the current calendar week.

## 7. Success Metrics
- 80% of daily check-ins completed in < 3 seconds from opening the page. (assumption)
- 70% 7-day retention rate for users who create at least 2 habits. (assumption)
