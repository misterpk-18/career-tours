---
name: career-tours-improvements
description: Resume the staged career-tours improvement plan — the remaining UX, correctness and long-operation phases from the July 2026 frontend audit. Use when picking that work back up, or when asked about the 73-second recommendation wait, the localStorage skills cache, the invisible upload/extract/generate pipeline, or the page-sameness cleanup.
---

# Career Tours: remaining improvement phases

A four-phase plan came out of an audit of this repo. **P0 (API authorization) and
Phase 1 (visual restraint) are shipped.** Three phases remain, listed here in the
order to do them — each is independently shippable.

Full original plan: `~/.claude/plans/the-website-looks-like-cheerful-adleman.md`
Detailed specs for each remaining phase: `references/` in this skill folder.

## Before starting

Read `references/context.md` first. It records what already shipped, the design
rules now enforced in code, and the environment facts that are easy to get wrong
(the DB password is not the one in the docs; there is no test suite or linter;
deploys are rsync-from-local because the box has neither Git nor Node).

## The remaining phases

### Phase 4 — client correctness (smallest, do first)
Four independent fixes, no migration, no backend work. See `references/phase-4-correctness.md`.

- `api.js` has **no axios timeout** — a hung backend spins forever.
- **No 401 response interceptor**, so an expired token surfaces as "Unable to load
  projects. Please try refreshing." on every page, forever, with no way back to login.
- `ProjectDetailsPage.jsx` renders `(skill.confidence_score || 1) * 100`, so a
  **missing** confidence displays as a confident green **100%**. Trust bug, not a
  formatting one.
- `App.jsx` silently redirects unknown URLs to `/`; needs a real `NotFoundPage`.

### Phase 3 — project state endpoint, and delete the localStorage cache
See `references/phase-3-state.md`. Add `GET /api/projects/<id>/state` (no migration),
then delete the `ct_skills_*` cache in `ProjectDetailsPage.jsx`.

That cache is the highest-severity item left: it violates the rule written at the top
of `lib/storage.js`, **survives logout** (so extracted skills leak between accounts on
a shared machine), is invisible on a second device, and goes stale after a new upload —
which flips the UI to "Skills Extracted" and **removes the Extract button**, locking
the user out. The same endpoint also kills a serial waterfall and an empty `catch` that
hides working features on a transient 500.

### Phase 2 — the 73-second wait (largest)
See `references/phase-2-jobs.md`. `POST /api/recommendations/projects/<id>/generate`
blocks for **73 seconds** (measured in production) behind a small spinning button with
no progress, ETA or cancel, and navigating away silently abandons it. It also occupies
one of only two gunicorn sync workers.

Approach: a `jobs` table + a one-slot worker thread per gunicorn process + client
polling. The alternatives (SSE, client-driven per-career requests, Celery/RQ) were
considered and rejected — the reasoning is in the reference so it isn't relitigated.
This is the only phase needing a migration (`006_jobs.sql`).

### Phase 1.7 — page sameness (cosmetic leftovers)
See `references/phase-1.7-layout.md`. Deferred from the shipped visual pass: extract
`PageActions`/`MasterDetail` helpers, drop the second hero from
`CourseRecommendationsPage`, and remove the now-callerless `icon` prop from
`SectionHeading`/`SectionLabel`.

## Verifying and deploying

Every phase ends the same way, and there is **no test suite or linter** — so verify
explicitly. `references/verify-deploy.md` has the exact commands: build, the
straggler greps, Playwright checks in light/dark at 1440px and 390px, the auth curl
matrix, and the rsync deploy.

Never regress these while working: the a11y layer (focus floor, forced-colors block,
`prefers-reduced-motion`, listbox semantics, focus trap, the throw-on-misuse guards)
and the colour contract at the top of `src/index.css`. Both are listed in
`references/context.md`.
