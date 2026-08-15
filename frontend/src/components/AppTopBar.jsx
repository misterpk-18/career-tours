import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Menu } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import GlobalSearch from './GlobalSearch';
import { resolveRoute } from '../lib/nav';

// Hidden below `sm`: three uppercase crumbs plus a hamburger and a back arrow
// do not fit on a phone, and the trail was being cut mid-word with no ellipsis.
// The back arrow is the part that has to survive, and it does.
const Breadcrumb = ({ trail }) => (
  <nav aria-label="Breadcrumb" className="hidden sm:block">
    <ol className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-widest text-fg-muted">
      {trail.map((crumb, index) => (
        <li key={`${crumb.label}-${index}`} className="flex items-center gap-1.5">
          {index > 0 ? <span aria-hidden="true">/</span> : null}
          {crumb.to ? (
            <Link
              to={crumb.to}
              className="rounded transition-colors hover:text-fg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              {crumb.label}
            </Link>
          ) : (
            // The last crumb is the current page, so it is not a link. Marking
            // it current is what a screen reader reads as "you are here".
            <span aria-current={index === trail.length - 1 ? 'page' : undefined}>{crumb.label}</span>
          )}
        </li>
      ))}
    </ol>
  </nav>
);

/**
 * The sticky bar above every page: where you are on the left, what you can do
 * from anywhere on the right.
 *
 * The back arrow and the breadcrumb both come from lib/nav.js rather than from
 * the page, which is what retired the four hand-written "Back to Project
 * Workspace" buttons that each named their destination slightly differently.
 */
export const AppTopBar = ({ onOpenSidebar }) => {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const route = resolveRoute(pathname);

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="flex h-16 items-center gap-3 px-4 lg:px-6">
        <button
          type="button"
          onClick={onOpenSidebar}
          aria-label="Open navigation"
          className="-ml-1 rounded-lg p-2 text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus lg:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>

        {route.parent ? (
          <button
            type="button"
            onClick={() => navigate(route.parent)}
            aria-label="Back"
            title="Back"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line bg-surface-2 text-fg-secondary transition-colors hover:bg-surface-3 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}

        <div className="min-w-0 flex-1">
          <Breadcrumb trail={route.trail} />
          <h2 className="truncate text-base font-bold tracking-tight text-fg">{route.title}</h2>
        </div>

        {/* Search takes the width it can get and disappears below `sm`, where the
            title and the controls already fill the bar. It stays reachable there
            through the pages themselves. */}
        <GlobalSearch className="hidden w-full max-w-xs sm:block lg:max-w-sm" />

        <ThemeToggle />
      </div>
    </header>
  );
};

export default AppTopBar;
