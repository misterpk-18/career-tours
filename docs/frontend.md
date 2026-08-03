# Frontend Guide (React + Vite)

The web client for Career Tours. It is a single-page application that talks to the Flask API documented in the root [README](../README.md).

---

## Tech Stack

| Concern | Choice |
|---|---|
| UI library | React 18.3 |
| Language | **Plain JavaScript with JSX** (`.jsx`) — there is no TypeScript setup, despite `@types/react` sitting unused in devDependencies |
| Build tool | Vite 5.4 (ESM, `"type": "module"`) |
| Routing | `react-router-dom` v6 |
| HTTP | `axios` (single shared instance) |
| Styling | Tailwind CSS 3.4 + a handful of hand-written utility classes |
| Icons | `lucide-react` |
| State | React `useState` / `useEffect` + one Context — no Redux, Zustand, or React Query |

`clsx` and `tailwind-merge` are installed but currently unused — there is no `cn()` helper in the codebase.

There is **no linter, formatter, or test framework** configured. The only quality gate is that `npm run build` succeeds.

---

## Scripts

```bash
cd frontend
npm install
npm run dev       # dev server on http://localhost:3000
npm run build     # production bundle -> frontend/dist/
npm run preview   # serve the built bundle locally
```

### The dev proxy and the port mismatch

`vite.config.js` proxies `/api` to `http://127.0.0.1:5001`:

```js
server: {
  port: 3000,
  proxy: { '/api': { target: 'http://127.0.0.1:5001', changeOrigin: true, secure: false } },
}
```

**Heads-up:** `backend/app.py` ends with `app.run(debug=True)`, which starts Flask on its default port **5000** — not 5001. Running `python backend/app.py` alongside `npm run dev` therefore gives you failing API calls.

Start the backend on 5001 instead:

```bash
cd backend && flask --app app run --port 5001 --debug
```

On macOS, 5000 is also claimed by the AirPlay Receiver service (it answers with `403`), which is the likely reason the proxy was pointed at 5001 in the first place. If you would rather use `python backend/app.py`, either disable AirPlay Receiver in *System Settings → General → AirDrop & Handoff* and change the proxy `target` in `vite.config.js` to `5000`, or change the `app.run()` call to `app.run(debug=True, port=5001)`.

Production does not use this proxy at all: Nginx serves `dist/` statically and routes `/api` to Gunicorn on port 5000. See [deployment.md](./deployment.md).

---

## Directory Layout

```text
frontend/
├── index.html              # app shell; pre-paint theme script + Google Fonts
├── vite.config.js          # dev server port + /api proxy
├── tailwind.config.js      # semantic colour aliases, type scale, two radii
├── postcss.config.js
├── dist/                   # build output (served by Nginx in production)
└── src/
    ├── main.jsx            # ReactDOM.createRoot -> <App />, imports index.css
    ├── App.jsx             # ALL routes + ProtectedRoute / PublicRoute wrappers
    ├── index.css           # design tokens, the colour contract, shared component classes
    ├── context/
    │   ├── AuthContext.jsx
    │   └── ThemeContext.jsx               # light | dark | system
    ├── components/
    │   ├── ui/                            # the design system (~25 primitives)
    │   ├── Navbar.jsx
    │   ├── ThemeToggle.jsx
    │   ├── CreateProjectModal.jsx
    │   ├── ResumeUploadModal.jsx
    │   └── ResumeViewerModal.jsx
    ├── hooks/              # useSubmit, useFocusTrap, useBodyScrollLock
    ├── lib/                # cn, storage, format, apiError
    ├── pages/
    │   ├── LoginPage.jsx
    │   ├── RegisterPage.jsx
    │   ├── HomePage.jsx                    # dashboard + project list
    │   ├── ProjectDetailsPage.jsx          # resume upload, skill extraction, generate recs
    │   ├── CareerRecommendationsPage.jsx   # top-5 career matches + skill gaps
    │   └── CourseRecommendationsPage.jsx   # gap-filling courses, grouped by career
    └── services/
        └── api.js          # the single axios module — every API call lives here
```

`components/ui/` is the design system: `Button`, `Card`, `TextField`, `Modal`,
`Chip`, `Badge`, `Alert`, `ProgressBar`, `StatTile`, `MetricTile`, `EmptyState`,
`SelectableCard`, `HeroBanner`, `PageShell` and friends. Build pages out of these
rather than raw Tailwind — the primitives own the a11y wiring (label/id association,
`role="listbox"` on selectable lists, focus trapping in modals, `aria-live` on
spinners), and several of them throw at runtime if misused.

`lib/storage.js` is the **only** module permitted to touch `localStorage`, and it
documents the rule: no server data in localStorage. Server-owned state is fetched
on mount.

There are no barrel `index.js` files and no path aliases — imports are relative
(`../services/api`).

---

## Routing

All routes live in [`src/App.jsx`](../frontend/src/App.jsx).

| Path | Access | Component |
|---|---|---|
| `/login` | public | `pages/LoginPage.jsx` |
| `/register` | public | `pages/RegisterPage.jsx` |
| `/` | protected | `pages/HomePage.jsx` |
| `/projects/:projectId` | protected | `pages/ProjectDetailsPage.jsx` |
| `/projects/:projectId/careers` | protected | `pages/CareerRecommendationsPage.jsx` |
| `/projects/:projectId/courses` | protected | `pages/CourseRecommendationsPage.jsx` |
| `*` | — | redirect to `/` |

Two wrappers, both defined in `App.jsx`:

- **`ProtectedRoute`** — renders a loading screen while the auth context rehydrates, redirects to `/login` when unauthenticated, otherwise renders `<Navbar />` plus the page inside `<main>`. Note the Navbar is rendered per route rather than as a layout route.
- **`PublicRoute`** — redirects an already-authenticated visitor to `/`.

### Adding a page

1. Create `src/pages/MyPage.jsx` with both a named and a default export (project convention: `export const MyPage = …` and `export default MyPage;`).
2. Import it in `App.jsx` and add a `<Route>` **above the `*` catch-all** — the catch-all must stay last or it will swallow the new path.
3. Add a way to reach it. There is no sidebar or nav config file: `components/Navbar.jsx` only holds the brand link and "Dashboard", so project-scoped pages are linked from `ProjectDetailsPage.jsx` (the action-button row) and from sibling pages' breadcrumbs.

---

## API Layer

Everything goes through [`src/services/api.js`](../frontend/src/services/api.js).

```js
const api = axios.create({
  baseURL: '/api',                                    // relative — proxied in dev, same-origin in prod
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('career_tours_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

`baseURL` is deliberately relative, so there are **no `import.meta.env` variables anywhere in the frontend** and no per-environment build.

Each method is `async` and returns `response.data` directly (not the axios response).

| Group | Methods |
|---|---|
| `authAPI` | `login`, `register` |
| `projectsAPI` | `create`, `getById`, `getByStudentId`, `getSkills`, `update`, `delete` |
| `resumesAPI` | `upload` (multipart override), `getById`, `getPreview`, `extractSkills`, `listMine` |
| `recommendationsAPI` | `generate`, `getCareers`, `getProjectOverview`, `getCareerDetails`, `getCourses`, `getCareerCourses` |

There is **no response interceptor**, so there is no global 401 handling or auto-logout — an expired token surfaces as a per-page error. Pages unwrap errors with the house convention:

```js
err.response?.data?.error || err.response?.data?.detail || 'Something went wrong'
```

### Data-fetching pattern

No data-fetching library. Pages hand-roll it: a `data` / `loading` / `error` state trio, an `async` fetch function, and a `useEffect` that calls it. `HomePage.jsx` is the cleanest example of the four-branch render (`loading` → `error` → empty → content); `CourseRecommendationsPage.jsx` extends it with a per-pane loading/error state plus a response cache keyed by occupation.

`ProjectDetailsPage.jsx` fetches a project's stored skills from `projectsAPI.getSkills` on mount. It used to cache them in `localStorage` under `ct_skills_${projectId}` instead, because no endpoint could answer "does this project have skills yet?". That cache is gone: it was server data in `localStorage`, which [`lib/storage.js`](../frontend/src/lib/storage.js) forbids, and it was wrong in any second browser — the cache was empty there, so a project whose skills were already in the database presented as though nothing had been extracted.

### Gotcha: numeric columns arrive as strings

PostgreSQL `numeric` values are returned by the API as JSON **strings**, e.g. `"85.00"`, because Flask serializes Python `Decimal` that way. This affects `match_percentage`, `coverage_percentage`, `gap_percentage`, `average_salary`, and `duration_hours`.

Always coerce before arithmetic or inline styles — `` style={{ width: `${"85.00"}%` }} `` renders, but `"85.00" + "10.00"` concatenates and `Math.round("85.00" * 1.1)` is a silent trap:

```js
const toPct = (v) => Math.max(0, Math.min(100, Math.round(Number(v) || 0)));
```

---

## Auth & Session

[`src/context/AuthContext.jsx`](../frontend/src/context/AuthContext.jsx) exposes `{ student, token, loading, isAuthenticated, login, register, logout }` via a `useAuth()` hook (which throws if used outside the provider).

- Persistence: `localStorage` keys `career_tours_token` (JWT string) and `career_tours_student` (JSON).
- On mount, a `useEffect` rehydrates both and flips `loading` to `false`; corrupt JSON clears the session.
- `isAuthenticated` is `!!token && !!student`.
- `logout()` clears state and both keys. There is no token-expiry check on the client — the backend rejects expired tokens with `{"error": "token expired"}`.

Every request carries the token: the axios instance in `src/services/api.js` attaches
`Authorization: Bearer <token>` from `lib/storage.js` in a request interceptor, and
nothing in `src/` calls `fetch` or bare `axios`, so there is no path that bypasses it.

**The API enforces this.** Every route except `POST /api/auth/register` and
`POST /api/auth/login` requires `@require_auth` *and* checks that the row belongs to
the caller — see `backend/api/guards.py`. A row owned by another student returns
**404, not 403**, because a 403 confirms the id exists. Two consequences for frontend
work:

- Any new endpoint must be called with the shared `api` instance, or it gets a 401.
- Passing a `student_id` in a request body is pointless; the server takes the owner
  from the token. `POST /api/projects` ignores a body-supplied `student_id`.

There is still no client-side expiry check and no 401 response interceptor, so an
expired token currently surfaces as a generic "unable to load" error on every page
rather than a redirect to login.

---

## Styling Conventions

Light and dark, driven by `data-theme` on `<html>` (see `ThemeContext` + the
pre-paint script in `index.html`). All colour, elevation and radius comes from CSS
custom properties defined once in `src/index.css` and exposed to Tailwind through
`tailwind.config.js`. `index.html` loads Plus Jakarta Sans only.

### The colour contract

This is the rule that keeps the UI from drifting back into a template, and it is
repeated at the top of both `src/index.css` and `src/lib/cn.js`:

> `brand` (indigo) is the **only** decorative colour — identity, selection, primary
> action, links, model-generated content. `success` / `warning` / `danger` are
> **state only**: legal iff the thing they label can be good, at-risk, or failed.
> A category, a rank, a difficulty and a percentage are none of those.

Concretely, this is why a match percentage renders in `text-fg` rather than green, why
course difficulty is a neutral chip rather than a purple/amber/green traffic light, and
why the three dashboard counters share one colour.

Two structural radii: **`rounded-xl`** for any box, **`rounded-lg`** for a box nested
inside a box, `rounded-full` for pills. `md`, `2xl` and `3xl` are deliberately absent
from the `borderRadius` config, so `rounded-2xl` compiles to nothing rather than
creeping back in.

### Shared classes in `src/index.css`

| Class | Use |
|---|---|
| `.surface-panel` | Static containers — page heroes, detail panels (opaque) |
| `.surface-panel-interactive` | Clickable cards; hover changes border + elevation |
| `.field` | Text inputs, with a brand focus border |
| `.btn-brand` | The one filled button |
| `.scrim` | Modal backdrop |

Reach for the primitives in `src/components/ui/` before these — a raw class usually
means a component is missing.

### Enforced by code, not convention

There is no linter in this project, so the rules are enforced where they can fail loudly:

- `Chip` and `Badge` **throw** on an unknown `tone`; `SectionHeading` and `EmptyState`
  throw when the heading level is omitted.

  Know the cost of that choice: a throw during render reaches `ErrorBoundary`, so a
  wrong tone string replaces the **entire page** with "Something went wrong" — not a
  mis-coloured chip. `CareerRecommendationsPage` passed the removed `tone="success"`
  for its "Strengths" list and took the careers page down completely. When a tone is
  deleted from a primitive, grep every call site in the same commit; and note that
  `Badge` and `Chip` do *not* accept the same tones (`Badge` has `success`, `Chip`
  deliberately does not), so a tone valid on one is a page-killer on the other.
- `Card` has no `radius` or `bordered` prop, `StatTile` no `tone`, `MetricTile` no
  `iconTone`, `HeroBanner` no `orbTone`/`eyebrowTone`, `Chip` no `dot`. Deleting the
  prop is what prevents the drift; a convention note would not.
- `tailwind.config.js` no longer defines `accent`, the raw `brand.50–950` ramp,
  `shadow-glass`, `animate-float` or `animate-pulse-slow`.

### Deliberately absent

Gone in the restraint pass, and not to be re-added without a reason that beats the one
for removing them: the tri-hue `.text-gradient` (it was on every page's `h1`, the
wordmark, *and* every progress-bar fill, so a bar's hue changed with its value while
meaning nothing); `backdrop-filter` glass (nothing behind it to blur on a near-white
canvas); the blurred decorative orbs and the page-wide `.app-aura`; coloured glow
shadows and hover translate; `font-extrabold`; uppercase `tracking-wider` form labels;
and `Sparkles` as a generic "AI happened here" glyph — it survives on exactly one
control, the one that actually calls the model.

### Composition patterns

- Page shell: `<PageShell>` → `max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8`
- Master–detail: `grid grid-cols-1 lg:grid-cols-12 gap-8` with `lg:col-span-5` +
  `lg:col-span-7`. **Known gap:** below `lg` the detail pane stacks below the list and
  nothing scrolls to it, so on a phone tapping a card looks like nothing happened.
- Model-generated content: `<AiInsightBox>` — a left rule, not a nested tinted box
- Loading: `<PageSpinner>` / `<PaneSpinner>` / `<Button loading>`; there are no skeletons
- Errors: `<Alert tone="error">` (`role="alert"`); other tones are `role="status"`

---

## Page Notes

### `ProjectDetailsPage.jsx`
The workspace hub. Resume upload, skill extraction, and the "Recommend Careers" trigger (`recommendationsAPI.generate`) — a single call that generates career matches, skill gaps, **and** course recommendations server-side.

The pipeline is strictly sequential, and the action row shows only the step that is actually available. Both inputs to that decision come from the server — `projectsAPI.getSkills` and `recommendationsAPI.getProjectOverview` — never from client state:

| Project state | Controls shown |
|---|---|
| no resume | upload only (banner + warning alert) |
| resume, no skills | "Extract skills" |
| skills extracted | *Skills Extracted* badge, "Recommend Careers" |
| recommendations exist | "View Recommended Careers", "View Recommended Courses" |

"Extract skills" is **removed** rather than rendered disabled when there is no resume: a dead button invites the click it then refuses, and the upload affordance already appears twice on the page.

### `CareerRecommendationsPage.jsx`
Master–detail over the top 5 career matches. The left list comes from `getProjectOverview`; selecting a career lazily calls `getCareerDetails` for its AI summary and skill gaps.

### `CourseRecommendationsPage.jsx`
Courses that close the skill gaps, **grouped by career**. Left pane lists the recommended careers with a per-career course count (derived from the single `getProjectOverview` response, so no extra requests). Selecting a career calls `getCareerCourses(projectId, occupationId)` — the only endpoint that joins the per-course AI summaries — and caches the result in a `coursesByCareer` map, so re-selecting is instant. Each course card shows its rank, level, duration, a "Skill Gap Coverage" bar, and the AI summary when present.

The two course endpoints are not interchangeable:

| Endpoint | Scope | Includes `summary`? |
|---|---|---|
| `GET /api/recommendations/projects/<id>/courses` | all careers, flattened | no |
| `GET /api/recommendations/projects/<id>/careers/<occupation_id>/courses` | one career | yes |
