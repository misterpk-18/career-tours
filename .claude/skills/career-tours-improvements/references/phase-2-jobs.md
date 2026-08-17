# Phase 2 — the 73-second wait

**Status: shipped.** Kept as a record of why this shape was chosen. Note that it was
written against the pre-Lambda runtime, so the worker-thread mechanism below was
superseded during implementation: Lambda freezes the sandbox the moment the handler
returns, so the job is run by the function re-invoking *itself* with
`InvocationType='Event'`. The problem statement and the rejected alternatives still hold.

## The problem

`POST /api/recommendations/projects/<id>/generate` took **73 seconds** in production
(measured: 5 careers + 16 courses). It is fully synchronous, and the client treatment is
one `await` behind a spinning button reading "Analysing…" — no progress, no ETA, no
stage breakdown, no cancel. The rest of the page stays interactive, so navigating away
silently abandons the result: the work completes server-side but the UI never learns.

It also holds a request slot open for those 73 seconds, and the infra papered over that
with a long read timeout rather than fixing the UX. On the current runtime it cannot be
papered over at all: API Gateway caps its integration timeout at 30 s and that limit
cannot be raised, so async is mandatory rather than merely better.

`POST /api/resumes/<id>/extract-skills` is the same shape at ~30s.

## Chosen approach: `jobs` table + one-slot worker thread + client polling

The enabling fact: every repository uses Flask-SQLAlchemy's `db.session`, so a thread
that opens its own `app.app_context()` gets its own session and **every existing
repository works unchanged**.

### Rejected alternatives — do not relitigate

- **SSE / streaming response** — holds the response open for the full 73s, which *is*
  the problem: sync workers cannot multiplex, so two concurrent students wedge the box.
  A backgrounded phone tab also drops the stream with no server-side record.
- **Client-driven per-career requests** — makes the browser the scheduler, so closing the
  tab abandons a half-written project. Worse than today, because the deletes have
  already run by then.
- **Celery / RQ** — no broker installed, and a 1 GB box already loads MiniLM into two
  worker processes.

## Work

### `backend/migrations/006_jobs.sql`
Follow the existing numbered-SQL convention (`IF NOT EXISTS`, comment header explaining
intent). Columns: `job_id`, `student_id`, `project_id`, `job_type`, `status`
(queued/running/succeeded/failed/cancelled), `stage`, `stage_done`, `stage_total`,
`percent`, `message`, `error`, `result jsonb`, `cancel_requested`, `heartbeat_at`,
`created_at`, `started_at`, `finished_at`.

Include a **partial unique index** on `(project_id, job_type) WHERE status IN
('queued','running')`. That is the real double-submit guard — it holds across every
concurrent execution, which no Python-side flag can. Add `backend/table_schemas/jobs.sql`
to match convention.

### `backend/repositories/job_repository.py`
Static-method class, raw SQL via `db.session.execute(text(...))`, mirroring
`project_repository.py`. Return `dict(row._mapping)` — no dataclass needed. Needs
`create` (caller catches `IntegrityError` from the partial index → attach to the
existing job), `get_by_id`, `get_latest`, `get_active`, `update_progress` (also sets
`heartbeat_at`), `mark_running`/`mark_succeeded`/`mark_failed`, `request_cancel`, and
`reap_stale(interval)` which fails any job whose heartbeat is older than ~120s.

### `backend/services/jobs/runner.py`
Module-level `ThreadPoolExecutor(max_workers=1)` → one job per worker process, two per
box. That is the RAM cap. `submit()` wraps the callable in `with app.app_context():`,
rolls back and `mark_failed` on exception, and **always** writes a terminal status in
`finally` — a job must never be left `running` by a Python exception. Throttle progress
writes to ~1 per 1.5s (but always on a stage transition) so 30 LLM completions do not
become 30 UPDATEs.

### `backend/api/jobs/routes.py`
- `GET /api/jobs/<id>` — `@require_auth`, **404** if the job belongs to another student.
  Call `reap_stale()` first so a poll after a deploy resolves to `failed` rather than
  hanging on `running` forever.
- `POST /api/jobs/<id>/cancel`
- `GET /api/projects/<id>/jobs/latest?type=` (on the projects blueprint) — how a reloaded
  page or a second device re-attaches, with **no client-side storage**, honouring the
  `lib/storage.js` rule.

### Progress granularity — be honest
Obtainable with small local edits: `matching` (occupation count known up front),
`career_summaries` (exactly 5 — swap `executor.map` for `submit` + `as_completed`, which
also stops exceptions being silently dropped), `persisting`, `courses` (5 careers known;
courses-per-career only known once that career's `course_scores` is ranked).

A true global "x of N LLM calls" is **not** obtainable without real refactoring, since N
is `5 + Σnᵢ`. So use a fixed-weight stage model computed server-side —
matching 15% / career_summaries 25% / persisting 5% / courses 55% — monotonic by
construction, degrading to an indeterminate bar when a stage total is unknown.

**Cancellation is also limited:** an in-flight OpenAI call cannot be aborted, so cancel
is checked at stage boundaries and means "stops within ~15s". And because the generator
deletes before rewriting, a cancelled run must tell the user *"cancelled — no
recommendations were saved, run it again"* rather than showing an empty careers page.

### Client
`hooks/useJob.js` (re-attach on mount, adaptive `setTimeout` polling 1s → 2.5s → 4s —
not `setInterval`, so a slow response cannot stack — pause on `document.hidden`,
`AbortController` on unmount), `lib/jobStages.js` (labels + an ETA that never counts
up), `components/JobProgress.jsx` reusing `ProgressBar` and `Alert tone="info"`
(`role="status"`, so it announces without stealing focus).

`handleRecommendCareers` stops awaiting the work and **stops auto-navigating**. Include
the sentence that changes the experience: *"This keeps running if you leave this page."*

### Rollout — three independently deployable releases
1. Async behind `?async=1`; sync remains the default. Old frontend keeps working.
2. Frontend switches to `?async=1`. **This is the release that fixes the problem.**
3. Async becomes the default; keep `?sync=1` for Postman/ops with a comment that it
   blocks for ~73s and therefore cannot be used through API Gateway's 30 s cap.

Apply the same treatment to `extract-skills` last (single `gpt-5` call, so honestly two
stages and an indeterminate bar).

## Verification

Apply `006_jobs.sql`, then `POST …/generate?async=1` and poll — assert percent is
monotonic and a terminal status always arrives. The behavioural tests matter more:

- Start a generation, **navigate away, come back**, and confirm the UI re-attaches.
- `sudo systemctl restart career-tours` mid-job; the next poll must report "interrupted",
  not hang on `running`.
- Concurrent double-submit returns the **same** job id (the partial index).
- Cancel resolves within ~15s and states that nothing was saved.
