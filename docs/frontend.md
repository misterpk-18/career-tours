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
├── index.html              # app shell; sets the dark body background + Google Fonts
├── vite.config.js          # dev server port + /api proxy
├── tailwind.config.js      # brand palette, fonts, custom animations
├── postcss.config.js
├── dist/                   # build output (served by Nginx in production)
└── src/
    ├── main.jsx            # ReactDOM.createRoot -> <App />, imports index.css
    ├── App.jsx             # ALL routes + ProtectedRoute / PublicRoute wrappers
    ├── index.css           # Tailwind directives + shared .glass-* / .gradient-* classes
    ├── context/
    │   └── AuthContext.jsx
    ├── components/
    │   ├── Navbar.jsx
    │   ├── CreateProjectModal.jsx
    │   ├── ResumeUploadModal.jsx
    │   └── ResumeViewerModal.jsx
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

There are no `hooks/`, `utils/`, `layouts/`, or barrel `index.js` files, and no path aliases — imports are relative (`../services/api`).

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
| `projectsAPI` | `create`, `getById`, `getByStudentId`, `update`, `delete` |
| `resumesAPI` | `upload` (multipart override), `getById`, `getPreview`, `extractSkills`, `listMine` |
| `recommendationsAPI` | `generate`, `getCareers`, `getProjectOverview`, `getCareerDetails`, `getCourses`, `getCareerCourses` |

There is **no response interceptor**, so there is no global 401 handling or auto-logout — an expired token surfaces as a per-page error. Pages unwrap errors with the house convention:

```js
err.response?.data?.error || err.response?.data?.detail || 'Something went wrong'
```

### Data-fetching pattern

No data-fetching library. Pages hand-roll it: a `data` / `loading` / `error` state trio, an `async` fetch function, and a `useEffect` that calls it. `HomePage.jsx` is the cleanest example of the four-branch render (`loading` → `error` → empty → content); `CourseRecommendationsPage.jsx` extends it with a per-pane loading/error state plus a response cache keyed by occupation.

`ProjectDetailsPage.jsx` additionally caches extracted skills in `localStorage` under `ct_skills_${projectId}`.

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

> **Backend caveat:** only `GET /api/resumes/mine` and `GET /api/resumes/<id>/preview` actually enforce `@require_auth`. The other routes accept ids from the URL or body without verifying ownership, so the frontend's auth is presentation-level for those paths.

---

## Styling Conventions

Dark theme only — there is no light mode or theme toggle. `index.html` sets the base classes and loads Plus Jakarta Sans + Inter from Google Fonts; `src/index.css` sets a fixed radial-gradient body background.

Shared classes defined in `src/index.css` (use these instead of re-inventing the look):

| Class | Use |
|---|---|
| `.glass-panel` | Large translucent containers — page heroes, detail panels |
| `.glass-card` | Interactive cards; includes a hover lift + brand-tinted border |
| `.glass-input` | Text inputs, with a brand focus ring |
| `.gradient-text` | Indigo → purple → emerald text gradient for headline accents |
| `.gradient-button` | Primary indigo CTA |
| `.gradient-button-emerald` | Secondary/confirm emerald CTA |

From `tailwind.config.js`: the `brand` palette (indigo 50–950), `font-sans` → Plus Jakarta Sans, and the `pulse-slow` / `float` animations. Tailwind's default `emerald`, `amber`, `slate`, and `purple` scales remain available (`extend` merges rather than replaces).

Recurring composition patterns, worth copying verbatim for visual consistency:

- Page shell: `max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8`
- Master–detail: `grid grid-cols-1 lg:grid-cols-12 gap-8` with `lg:col-span-5` + `lg:col-span-7`
- Hero banner: `glass-panel rounded-3xl p-8 relative overflow-hidden` plus an absolutely-positioned `blur-3xl` glow div
- Progress bar: `w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800` wrapping a `bg-gradient-to-r from-brand-500 via-indigo-500 to-emerald-400` fill
- Loading: `<Loader2 className="w-10 h-10 animate-spin text-brand-400" />`
- Error alert: `bg-red-950/60 border border-red-800/60 text-red-200`
- AI-generated content: `bg-brand-950/30 border border-brand-800/40` with a `Sparkles` heading

---

## Page Notes

### `ProjectDetailsPage.jsx`
The workspace hub. Resume upload, skill extraction, and the "Recommend Careers" trigger (`recommendationsAPI.generate`) — a single call that generates career matches, skill gaps, **and** course recommendations server-side. Once generated, the action row offers "View Recommended Careers" and "View Recommended Courses".

### `CareerRecommendationsPage.jsx`
Master–detail over the top 5 career matches. The left list comes from `getProjectOverview`; selecting a career lazily calls `getCareerDetails` for its AI summary and skill gaps.

### `CourseRecommendationsPage.jsx`
Courses that close the skill gaps, **grouped by career**. Left pane lists the recommended careers with a per-career course count (derived from the single `getProjectOverview` response, so no extra requests). Selecting a career calls `getCareerCourses(projectId, occupationId)` — the only endpoint that joins the per-course AI summaries — and caches the result in a `coursesByCareer` map, so re-selecting is instant. Each course card shows its rank, level, duration, a "Skill Gap Coverage" bar, and the AI summary when present.

The two course endpoints are not interchangeable:

| Endpoint | Scope | Includes `summary`? |
|---|---|---|
| `GET /api/recommendations/projects/<id>/courses` | all careers, flattened | no |
| `GET /api/recommendations/projects/<id>/careers/<occupation_id>/courses` | one career | yes |
