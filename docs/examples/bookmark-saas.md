# Bookmark Manager SaaS PRD

> **For AI agents:** This document is your implementation instruction. Where it is unclear, do not guess — ask the user. When a decision changes during implementation, update this document so it remains the source of truth (living document). Items marked `(assumption)` were not confirmed by the user — verify them before relying on them.

## 1. Overview
Current bookmark managers suffer from cluttered organizational hierarchies and lack frictionless saving across workflows. This product provides a lightweight Next.js web application and Chrome extension to capture bookmarks seamlessly and organize them with tag-based filtering. The goal is to reduce link retrieval time for power web users.

## 2. Target Users & JTBD
- **Target Users:** Knowledge workers, researchers, and developers who save 10+ links daily.
- **Jobs to Be Done:** When browsing technical articles or reference documentation, users want to save links with a single shortcut so they can find them later within 3 seconds using tag filters.

## 3. Core Features (Scope)
1. **Chrome Extension Saver** — Instant bookmark saving popup with auto-extracted title, metadata, and quick tag inputs.
2. **Web Dashboard** — Responsive dashboard to browse, search, edit, and bulk-tag saved bookmarks.
3. **Authentication & Data Sync** — User login via Supabase Auth with real-time PostgreSQL database persistence.

## 4. Non-Goals
- AI-based auto-tagging suggestions are not implemented in this version.
- Paid subscription billing and Stripe checkout are not implemented in this version.
- Multi-user collaborative workspace sharing is not implemented in this version.
- Browser extensions for Firefox or Safari are not supported in this version.
- Folder/collection-based classification is not implemented in this version (tags cover it).

## 5. Technical Constraints & Prior Decisions
- Framework: Next.js 14 App Router on Vercel [DO NOT CHANGE]
- Database & Auth: Supabase (PostgreSQL + Row Level Security) [DO NOT CHANGE]
- Extension: Manifest V3 Chrome Extension
- Managed Data: URL, title, description, favicon_url, tags, created_at, user_id

## 6. Phased Requirements

### Phase 1: Core Extension and Storage Pipeline
**Goal:** Bookmarks saved from Chrome extension land correctly in the Supabase database.
**Requirements:**
1. Setup Next.js boilerplate and Supabase authentication tables.
2. Create Chrome Extension popup interface with URL and title auto-fill.
3. Implement POST /api/bookmarks endpoint with JWT token verification.
**Acceptance criteria:**
- [ ] User can authenticate in Chrome extension via Supabase OAuth.
- [ ] After login, the save button is reachable within 2 clicks from the extension icon.
- [ ] Clicking save creates a new record in the Supabase `bookmarks` table within 500ms.
- [ ] Re-saving the same URL updates the existing record instead of creating a duplicate.

### Phase 2: Web Management Dashboard
**Goal:** Users can browse, search, and tag their saved bookmarks in a clean web UI.
**Requirements:**
1. Build responsive list and card views for bookmarks.
2. Implement instant client-side search by title and tags.
3. Support tag management (create, assign, remove tags).
**Acceptance criteria:**
- [ ] Dashboard displays all user bookmarks with pagination (20 per page).
- [ ] Searching a keyword updates displayed list in < 100ms.
- [ ] Tag clicks filter the bookmark stream accurately.

## 7. Success Metrics
- Average time to save a bookmark from extension is under 2 seconds.
- 95% of user link searches complete in under 3 seconds.
