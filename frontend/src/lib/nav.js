import { Compass, FolderKanban, GraduationCap, LayoutDashboard } from 'lucide-react';

/**
 * Where the shell thinks the user is.
 *
 * ONE table, read by the sidebar's active state, the breadcrumb, the back arrow
 * and the search box. They previously disagreed by construction: each page hand
 * wrote its own "Back to Project Workspace" button, so the label, the target and
 * the highlighted nav item were three independent guesses at the same fact.
 *
 * Order matters — most specific first. `/projects/x/careers` must not be
 * answered by the `/projects/:projectId` entry.
 */
const ROUTES = [
  {
    key: 'careers',
    pattern: /^\/projects\/([^/]+)\/careers\/?$/,
    title: 'Career Matching',
    trail: (id) => [
      { label: 'Portal', to: '/' },
      { label: 'Project', to: `/projects/${id}` },
      { label: 'Career Matching' },
    ],
    parent: (id) => `/projects/${id}`,
  },
  {
    key: 'courses',
    pattern: /^\/projects\/([^/]+)\/courses\/?$/,
    title: 'Recommended Courses',
    trail: (id) => [
      { label: 'Portal', to: '/' },
      { label: 'Project', to: `/projects/${id}` },
      { label: 'Courses' },
    ],
    parent: (id) => `/projects/${id}`,
  },
  {
    key: 'project',
    pattern: /^\/projects\/([^/]+)\/?$/,
    title: 'Project Workspace',
    trail: () => [
      { label: 'Portal', to: '/' },
      { label: 'Projects', to: '/' },
      { label: 'Workspace' },
    ],
    parent: () => '/',
  },
  {
    key: 'dashboard',
    pattern: /^\/$/,
    title: 'Dashboard',
    trail: () => [{ label: 'Portal' }, { label: 'Dashboard' }],
    parent: () => null,
  },
];

/**
 * Resolve a pathname to the chrome the shell should show around it.
 *
 * Always returns an object. An unmatched path is a route the catch-all is about
 * to redirect away from, and rendering a blank header for one frame is better
 * than making every consumer null-check.
 */
export const resolveRoute = (pathname) => {
  for (const route of ROUTES) {
    const match = route.pattern.exec(pathname);

    if (!match) continue;

    const projectId = match[1] || null;

    return {
      key: route.key,
      projectId,
      title: route.title,
      trail: route.trail(projectId),
      parent: route.parent(projectId),
    };
  }

  return { key: null, projectId: null, title: '', trail: [], parent: null };
};

/** Nav items that exist regardless of what the user is looking at. */
export const PRIMARY_NAV = [
  { key: 'dashboard', label: 'Dashboard', description: 'Your projects', icon: LayoutDashboard, to: '/' },
];

/**
 * Nav items for the project currently open, or `[]` when none is.
 *
 * These are the shell's answer to a real constraint: career matches and course
 * recommendations are project-scoped routes, so they cannot sit in the global
 * rail the way the mock draws them. Surfacing them contextually keeps the same
 * shape without inventing a `/courses` page that has no endpoint behind it.
 */
export const projectNav = (projectId) =>
  projectId
    ? [
        { key: 'project', label: 'Overview', icon: FolderKanban, to: `/projects/${projectId}` },
        { key: 'careers', label: 'Career Matching', icon: Compass, to: `/projects/${projectId}/careers` },
        { key: 'courses', label: 'Courses', icon: GraduationCap, to: `/projects/${projectId}/courses` },
      ]
    : [];
