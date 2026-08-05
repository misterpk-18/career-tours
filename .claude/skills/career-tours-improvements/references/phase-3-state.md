# Phase 3 — project state endpoint, and deleting the localStorage skills cache

Highest-severity remaining item. No migration.

## The problem

`frontend/src/pages/ProjectDetailsPage.jsx` caches extracted skills in
`localStorage` under `ct_skills_<projectId>`, with a comment admitting it is temporary
and exists "only because there is no GET endpoint for a project's skills yet".

That is still true — there is no `GET /api/projects/<id>/skills`. The consequences are
all real and all live:

1. **It violates the rule written at the top of `frontend/src/lib/storage.js`**, which
   declares itself the only module permitted to touch localStorage and states: no server
   data in localStorage, because "two sources of truth previously made 188 extracted
   skills unreachable in the UI while they sat in the database." `ProjectDetailsPage`
   calls `localStorage.getItem` directly with server data.
2. **It survives logout.** `clearSession()` deliberately clears only the two auth keys,
   so `ct_skills_*` persists. On a shared machine, the next student sees the previous
   student's extracted skills for any project id still cached.
3. **It is device-local.** The same account on a phone shows "No skills extracted yet"
   for a project with skills in the database.
4. **It goes stale after a new upload.** `onResumeUploaded` → `fetchProjectData()`
   rehydrates from the cache, so old-resume skills display alongside a new resume with
   `skillsAlreadyExtracted = true` — which **removes the Extract button entirely** and
   replaces it with a green "Skills Extracted" badge. The user is locked out of
   re-extracting with no visible escape.

The page already knows this pattern is wrong: the career/course "View" buttons were
re-gated on an API flag precisely because "on a fresh browser the cache is empty even
though recommendations exist server-side, which used to hide these buttons entirely."
The skills grid never got the same treatment.

## The fix

Add **`GET /api/projects/<project_id>/state`** to `backend/api/projects/routes.py`
(`@require_auth` + `owned_project()` like every other route there). Return in one call:

- the project
- its skills — `ProjectSkillRepository.get_by_project_id` already exists, and
  `_serialize_skill` in `backend/api/resumes/routes.py` is the serializer to reuse (move
  it somewhere shared rather than duplicating)
- counts: skills, careers (`CareerMatchRepository`), courses (`CourseRecommendationRepository`)
- a single canonical `pipeline` object derived **server-side**:
  `{ step: 1|2|3, resume: 'missing'|'ready', skills: 'blocked'|'ready'|'done', recommendations: 'blocked'|'ready'|'done' }`

Computing `pipeline` in one place is the point: the client currently keeps three
booleans (`skillsAlreadyExtracted`, `careersAlreadyGenerated`, `skills.length > 0`) that
can and do disagree.

Then in `ProjectDetailsPage.jsx`:

- Delete `SKILLS_CACHE_KEY`, `getCachedSkills`, `setCachedSkills` and every call.
- Replace the **serial waterfall** (`await projectsAPI.getById` then
  `await recommendationsAPI.getProjectOverview`) with the single `/state` call.
- Delete the **empty catch** that treats a failed overview request as "no
  recommendations yet" — a transient 500 currently hides the View buttons. Surface a
  retriable `Alert` instead.

## Follow-on (same phase, optional)

Once `/state` exists, the invisible pipeline becomes fixable: `ProjectDetailsPage`'s
nested ternary can be replaced by a `PipelineSteps` component where every step's action
is **always rendered** (disabled with its reason inline, instead of vanishing), and the
dashboard cards can show real stage badges instead of the binary
`Resume Linked` / `Pending Resume`. See the original plan's Phase 3 for the full shape.

## Verification

- Two browser profiles: extract skills in one, confirm they appear in the other after a
  plain reload (they cannot today).
- Log out and in as a different student; confirm none of the first student's skills are
  visible anywhere.
- Upload a replacement resume and confirm the Extract control returns rather than the
  UI insisting skills are already extracted.
- `curl` the endpoint with another student's project id and confirm **404**.
