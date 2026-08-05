# Phase 4 — client correctness

Four independent fixes. No migration, no backend change. Smallest phase; do it first.

## 1. No axios timeout

`frontend/src/services/api.js` — the `axios.create({ baseURL, headers })` call has no
`timeout`, so a hung backend leaves the UI spinning on browser defaults with no failure
path.

- Add `timeout: 30000`.
- Override to `120000` for `resumesAPI.upload` only — S3 upload plus PDF parsing is
  still done in-request and legitimately takes longer.
- Do **not** set a short timeout globally before Phase 2 lands: `recommendationsAPI.generate`
  currently blocks for ~73s and would start failing client-side.

## 2. No 401 response interceptor

`api.js` installs a **request** interceptor only (it attaches the bearer token). There
is no response interceptor, so an expired JWT renders as
`"Unable to load projects. Please try refreshing."` on every page forever — the user is
stuck with a false error and no hint to sign in again.

Add a response interceptor: on `401`, call `clearSession()` from `lib/storage.js` and
redirect to `/login`. Two cautions:

- Do not redirect on a `401` from `POST /api/auth/login` itself — bad credentials are a
  normal 401 and must keep rendering the form error.
- `AuthContext` owns session state; clear through it (or trigger its logout) rather
  than writing localStorage from the interceptor, so React state and storage agree.

## 3. Fabricated confidence and proficiency

`frontend/src/pages/ProjectDetailsPage.jsx`, in the skill card:

```jsx
<span>Level {skill.proficiency_level || 5}/10</span>
Conf: {Math.round((skill.confidence_score || 1) * 100)}%
```

A **missing** confidence renders as `100%`, and a missing proficiency as a mid-range
`5/10`. Both are invented values presented as data — a trust bug, not a formatting one.

Render `—` when the value is null/undefined. Note `0` is a legitimate value, so test for
null explicitly rather than using `||`. `lib/format.js` is the right home for the helper
and already documents the Postgres-numeric-as-string coercion problem.

Also in the same card: `skill.source && skill.source.length <= 20 ? skill.source : 'Resume'`
uses a **string length** as a stand-in for a data contract. Now that summaries are
typed, decide what `source` is (a short provenance token vs free text) and enforce it
where it is written, not where it is displayed.

## 4. No 404 page

`frontend/src/App.jsx` ends its route list with `<Route path="*" element={<Navigate to="/" />} />`,
so a mistyped or stale URL silently teleports the user to the dashboard with no
explanation.

Add a `NotFoundPage` built from the existing `EmptyState` primitive (it needs
`titleAs="h1"` or it throws). Keep the redirect for `/` itself.

## Verification

No backend involved, so: `npm run build`, then click through login → dashboard →
project → careers → courses. Specifically check:

- With devtools throttling or the backend stopped, a request fails within ~30s instead
  of hanging.
- Hand-edit the token in localStorage to something invalid, reload, and confirm you land
  on `/login` rather than seeing a generic load error.
- A project whose skills lack confidence scores shows `—`, not `100%`.
- `/nonsense-url` renders the 404 page.
