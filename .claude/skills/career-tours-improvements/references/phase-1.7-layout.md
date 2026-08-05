# Phase 1.7 — page sameness (deferred cosmetic leftovers)

Deferred from the shipped visual pass. Purely structural; no behaviour change.

## The problem

All four authenticated pages open with a byte-identical stack: `PageShell` → a
breadcrumb row → `HeroBanner` with an eyebrow → `SectionHeading` → a grid. Two of them
are the *same* master/detail layout twice: `CareerRecommendationsPage` and
`CourseRecommendationsPage` share the same `grid-cols-1 lg:grid-cols-12` /
`col-span-5` + `col-span-7` wrapper, the same `RankBadge + h3 + line-clamp + ChevronRight`
left cards, and both `.slice(0, 5)`.

## Work

### 1. Extract the repeated strings into `PageShell.jsx` (~10 lines)
- **`PageActions`** — wraps `flex items-center justify-between gap-4 flex-wrap`, used at
  the top of `ProjectDetailsPage`, `CareerRecommendationsPage`, `CourseRecommendationsPage`.
- **`MasterDetail({ master, detail })`** — owns the 12-column grid and both column spans.

### 2. Drop the second hero from `CourseRecommendationsPage`
Replace its `HeroBanner` with `<SectionHeading as="h1">Courses to close your gaps</SectionHeading>`
plus a one-line `<p>`. The courses page is reached *from* the careers page; it does not
need a second full-height hero. **This is the single change that makes the two pages stop
reading as the same page**, and it removes a hero-sized block.

`SectionHeading` throws if `as` is omitted, which protects the `h1` here. Afterwards
confirm exactly one `h1` per page.

### 3. Remove the now-callerless `icon` prop
After the visual pass removed every icon that merely restated the words beside it
(`Layers` + "Your projects", `Award` + "Top 5 Ranked Careers", `Zap` + "Skills from your
resume", `Tag` + "Extracted Skills", `BookOpen` + "Skill Gaps to Bridge"), check whether
any caller still passes `icon`/`iconClassName` to `SectionHeading` or `SectionLabel`. If
none do, delete the props — that also removes the last `iconClassName="text-warning-fg"`
style one-offs.

Grep before deleting: some call sites may still pass an icon that is genuinely
informational.

## Verification

`npm run build`, then screenshot careers and courses side by side at 1440px and confirm
they no longer read as one page. Re-check the heading outline (one `h1`, no skipped
levels) with the accessibility tree.
