import {
  Compass,
  FolderKanban,
  GraduationCap,
  Home,
  LayoutDashboard,
  UserCircle,
} from 'lucide-react';

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
    key: 'careers-project',
    pattern: /^\/projects\/([^/]+)\/careers\/?$/,
    param: 'projectId',
    title: 'Career Matching',
    trail: (id) => [
      { label: 'Portal', to: '/' },
      { label: 'Project', to: `/projects/${id}` },
      { label: 'Career Matching' },
    ],
    parent: (id) => `/projects/${id}`,
  },
  {
    key: 'courses-project',
    pattern: /^\/projects\/([^/]+)\/courses\/?$/,
    param: 'projectId',
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
    param: 'projectId',
    title: 'Project Workspace',
    trail: () => [
      { label: 'Portal', to: '/' },
      { label: 'Projects', to: '/projects' },
      { label: 'Workspace' },
    ],
    parent: () => '/projects',
  },
  {
    key: 'projects',
    pattern: /^\/projects\/?$/,
    title: 'Projects',
    trail: () => [{ label: 'Portal', to: '/' }, { label: 'Projects' }],
    parent: () => '/',
  },
  {
    key: 'course',
    pattern: /^\/courses\/([^/]+)\/?$/,
    param: 'courseId',
    title: 'Learning Journey',
    trail: () => [
      { label: 'Portal', to: '/' },
      { label: 'Courses', to: '/courses' },
      { label: 'Journey' },
    ],
    parent: () => '/courses',
  },
  {
    key: 'courses',
    pattern: /^\/courses\/?$/,
    title: 'Course Catalogue',
    trail: () => [{ label: 'Portal', to: '/' }, { label: 'Courses' }],
    parent: () => '/',
  },
  {
    key: 'careers',
    pattern: /^\/careers\/?$/,
    title: 'Career Directory',
    trail: () => [{ label: 'Portal', to: '/' }, { label: 'Careers' }],
    parent: () => '/',
  },
  {
    key: 'profile',
    pattern: /^\/profile\/?$/,
    title: 'Update Profile Info',
    trail: () => [{ label: 'Settings', to: '/' }, { label: 'Profile' }],
    parent: () => '/',
  },
  {
    key: 'home',
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

    // Named, not positional. Reading match[1] as "the project id" made
    // /courses/<uuid> look like an open project, so the rail rendered a
    // "Current project" section whose links pointed at /projects/<courseId>.
    const id = route.param ? match[1] : null;

    return {
      key: route.key,
      projectId: route.param === 'projectId' ? id : null,
      courseId: route.param === 'courseId' ? id : null,
      title: route.title,
      trail: route.trail(id),
      parent: route.parent(id),
    };
  }

  return { key: null, projectId: null, courseId: null, title: '', trail: [], parent: null };
};

/**
 * The rail's main section.
 *
 * `home` and `projects` currently render the same page — the dashboard IS the
 * project list today. They are two routes rather than one nav entry pointing
 * twice so each highlights on its own path; collapsing them would light up two
 * items at once, and splitting them later needs no nav change.
 */
export const PRIMARY_NAV = [
  { key: 'home', label: 'Home', icon: Home, to: '/' },
  { key: 'projects', label: 'Projects', icon: FolderKanban, to: '/projects' },
  { key: 'courses', label: 'Courses', icon: GraduationCap, to: '/courses' },
  { key: 'careers', label: 'Careers', icon: Compass, to: '/careers' },
];

/** Pinned above the account block, per the reference layout. */
export const FOOTER_NAV = [{ key: 'profile', label: 'Profile', icon: UserCircle, to: '/profile' }];

/**
 * Nav items for the project currently open, or `[]` when none is.
 *
 * These are the shell's answer to a real constraint: a project's career matches
 * and course recommendations are project-scoped routes, so they cannot sit in
 * the global rail — the top-level Courses and Careers entries are the whole
 * catalogue, which is a different question from "what was recommended to me".
 */
export const projectNav = (projectId) =>
  projectId
    ? [
        { key: 'project', label: 'Overview', icon: LayoutDashboard, to: `/projects/${projectId}` },
        {
          key: 'careers-project',
          label: 'Career Matching',
          icon: Compass,
          to: `/projects/${projectId}/careers`,
        },
        {
          key: 'courses-project',
          label: 'Recommended Courses',
          icon: GraduationCap,
          to: `/projects/${projectId}/courses`,
        },
      ]
    : [];

/**
 * Which PRIMARY_NAV key counts as active for a route.
 *
 * A detail route highlights its section: reading a course's journey is still
 * "being in Courses", and anything under a project is still "being in
 * Projects". Leaving the rail unlit on those pages would say they belong to no
 * section at all.
 *
 * Only used for the primary rail. The contextual project items match on the
 * route key exactly, so "Career Matching" highlights without the top-level
 * "Careers" — the whole catalogue and this project's matches are different
 * questions and must not look like the same place.
 */
const SECTION_OF = {
  course: 'courses',
  project: 'projects',
  'careers-project': 'projects',
  'courses-project': 'projects',
};

export const activeNavKey = (routeKey) => SECTION_OF[routeKey] || routeKey;
