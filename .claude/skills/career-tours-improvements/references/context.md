# Context: what shipped, what is enforced, what to watch

## Already shipped (do not redo)

| Commit | What |
|---|---|
| `f2e23a7` | **P0 authorization.** `@require_auth` + ownership on every route except `auth/register` and `auth/login`. `backend/api/guards.py` holds `owned_project()`. Other students' rows return **404, not 403**. Owner comes from the token, never the body. `POST /api/students` deleted (it was an unauthenticated second signup path that skipped the password rules). |
| `1a8490a` | **Phase 1 visual restraint.** One accent colour. Deleted: `accent`/purple, the raw `brand.50–950` ramp, `.text-gradient`, `.btn-success`, `.app-aura`, the glass token set, `shadow-glass`, `animate-float`, `animate-pulse-slow`, `lib/courseLevel.js`. `.surface-glass*` → `.surface-panel*` (opaque). Props removed: `Card.radius`, `Card.bordered`, `StatTile.tone`, `MetricTile.iconTone`, `HeroBanner.orbTone`/`eyebrowTone`, `Chip.dot`. |
| `92b3dc9` | Blank profile fields stored as NULL (the `students_phone_key` collision that broke registration). |
| `e4d83b8` | `student_skills.source` widened to 100; extract-skills reuses stored skills instead of re-running the LLM; both skill tables now written in one transaction. |
| `07a3063` | Career/course summaries return typed sections (`gpt-5-mini`, `responses.parse`), stored as JSON in `summary_text`, exposed as `structured`. |

## Rules now enforced in code — do not undo

**The colour contract** (top of `src/index.css`, repeated in `src/lib/cn.js`):

> `brand` (indigo) is the only decorative colour. `success`/`warning`/`danger` are
> state only — legal iff the labelled thing can be good, at-risk, or failed. A
> category, a rank, a difficulty and a percentage are none of those.

Two structural radii: `rounded-xl` for any box, `rounded-lg` for a box inside a box,
`rounded-full` for pills. `md`/`2xl`/`3xl` are absent from the `borderRadius` config on
purpose, so `rounded-2xl` compiles to nothing.

**Runtime guards** (the project's idiom for enforcement, since there is no linter):
`Chip` and `Badge` throw on an unknown `tone`; `SectionHeading` and `EmptyState` throw
when the heading level is omitted; `IconButton` throws without a label.

## Never regress the a11y layer

This is the part of the codebase that was already good, and it is easy to break while
editing styles:

- `:focus-visible` outline floor in `index.css` (`outline`, not `box-shadow` — the only
  focus style that survives forced-colors).
- The `@media (forced-colors: active)` block. **Its selectors must track any rename of
  `.surface-panel*`.** A missed rename silently restores translucency for high-contrast
  users — this was the highest-risk edit of the visual pass.
- `@media (prefers-reduced-motion: reduce)`; the `@media (hover: hover) and
  (pointer: fine)` guards (on touch, `:hover` sticks after a tap).
- `role="progressbar"` + valuenow/min/max on `ProgressBar`, with `toPct` clamping
  internally; `listbox`/`option`/`aria-selected` + keyboard on `SelectableCard`;
  `radiogroup` on `ThemeToggle`; `role="alert"` vs `role="status"` in `Alert`;
  `aria-live` on the spinners; `aria-busy`/`aria-disabled` on `Button`.
- `Modal`'s portal + focus trap + scroll lock; `useFocusTrap` is hardened against
  StrictMode double-invoke; `useBodyScrollLock` is reference-counted.
- `FileDropzone` uses `sr-only` (not `display:none`) on its file input.

## Environment facts that are easy to get wrong

- **Live:** https://nipunacareers.com (and `www.`) — CloudFront `E1TW6HR68G4A7T` in front of
  an S3 bucket for the SPA and an API Gateway HTTP API for `/api/*`.
- **Runtime is AWS Lambda**, `career-tours-api` in `ap-south-1` — an arm64 **container image**
  from ECR, 1024 MB / 300 s. Deploy = `docker buildx` + `aws lambda update-function-code`.
  See [docs/architecture.md](../../../../docs/architecture.md) for the exact flags, which are
  not optional.
- **Logs are under a group override:** `/aws/lambda/career-tours-lambda`, *not* the default
  `/aws/lambda/career-tours-api`, which is empty.
- **API Gateway caps integration timeout at 30 s and it cannot be raised.** Both long
  endpoints are now async jobs behind `?async=1`; a background thread is not an option
  because Lambda freezes the sandbox when the handler returns.
- **The database is Neon**, and every environment including local development talks to that
  same endpoint over TLS. There is no local Postgres.
- **No test suite, no linter, no CI.** `npm run build` is the only automated gate.

## Known issues deliberately left open

- `generator.py` deletes then rewrites recommendations across five repositories that
  each commit independently, so a mid-run failure leaves a project with zero
  recommendations. Making it atomic means removing `db.session.commit()` from those
  repositories and committing once at the boundary.
- `backend/services/skills/taxonomy.py` and `backend/data/skill_taxonomy.json` have no
  importers yet.
- The register form still posts `phone: ''` rather than omitting it (the backend
  normalises it, so this is cosmetic).
- Every form field carries a decorative icon inside the input — flagged in the audit as
  a template tell, but removing it was outside the approved plan.
- `RegisterPage`'s `INITIAL_FORM` declares `branch_name` with no input rendered.
