import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronsLeft, ChevronsRight, Compass, LogOut, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { FOOTER_NAV, PRIMARY_NAV, activeNavKey, projectNav, resolveRoute } from '../lib/nav';
import { cn } from '../lib/cn';

const SectionLabel = ({ collapsed, children }) =>
  collapsed ? (
    // A rule rather than the word: collapsed to icons there is no room for a
    // heading, but the grouping it expresses still has to survive.
    <div className="mx-auto my-2 h-px w-6 bg-line" role="presentation" />
  ) : (
    <div className="px-3 pb-1.5 pt-4 text-2xs font-bold uppercase tracking-widest text-fg-muted">
      {children}
    </div>
  );

// Link, not NavLink. Active state comes from lib/nav.js, which knows that
// /courses/<id> is still the Courses section — NavLink only knows whether the
// path equals its own `to`, and it overwrites aria-current with that answer, so
// every detail route announced itself as belonging to no section.
const NavItem = ({ item, active, collapsed, onNavigate }) => (
  <Link
    to={item.to}
    onClick={onNavigate}
    // `title` is the only affordance left when the label is hidden, and
    // aria-current is what tells a screen reader which one is open — the visual
    // fill alone announces nothing.
    title={collapsed ? item.label : undefined}
    aria-current={active ? 'page' : undefined}
    className={cn(
      'group relative flex items-center rounded-lg text-sm font-semibold transition-colors',
      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
      collapsed ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2.5',
      active
        ? 'bg-brand-subtle text-brand-subtle-fg'
        : 'text-fg-secondary hover:bg-surface-2 hover:text-fg'
    )}
  >
    <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
    {collapsed ? <span className="sr-only">{item.label}</span> : <span className="truncate">{item.label}</span>}
  </Link>
);

/**
 * The persistent nav rail.
 *
 * Rendered once by AppLayout and reused for the mobile drawer, so the two can
 * never drift apart — the drawer is this component in a sliding container, not
 * a second copy of the nav.
 */
export const AppSidebar = ({ collapsed, onToggleCollapse, onNavigate }) => {
  const { student, logout } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  const route = resolveRoute(pathname);
  const contextual = projectNav(route.projectId);
  const section = activeNavKey(route.key);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const initial = student?.full_name?.trim()?.charAt(0)?.toUpperCase();

  return (
    <div className="flex h-full flex-col border-r border-line bg-surface">
      {/* Brand */}
      <div
        className={cn(
          'flex h-16 shrink-0 items-center border-b border-line',
          collapsed ? 'justify-center px-2' : 'gap-2.5 px-4'
        )}
      >
        <Link
          to="/"
          onClick={onNavigate}
          className="flex min-w-0 items-center gap-2.5 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl btn-brand">
            <Compass className="h-5 w-5 text-fg-on-solid" aria-hidden="true" />
          </span>
          {collapsed ? null : (
            <span className="truncate text-base font-bold tracking-tight text-fg">CareerTours</span>
          )}
        </Link>

        {collapsed ? null : (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
            className="ml-auto hidden rounded-lg p-1.5 text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus lg:block"
          >
            <ChevronsLeft className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav aria-label="Main" className="flex-1 overflow-y-auto px-2 py-3">
        <ul className="space-y-1">
          {PRIMARY_NAV.map((item) => (
            <li key={item.key}>
              <NavItem
                item={item}
                active={section === item.key}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            </li>
          ))}
        </ul>

        {contextual.length ? (
          <>
            <SectionLabel collapsed={collapsed}>Current project</SectionLabel>
            <ul className="space-y-1">
              {contextual.map((item) => (
                <li key={item.key}>
                  <NavItem
                    item={item}
                    active={route.key === item.key}
                    collapsed={collapsed}
                    onNavigate={onNavigate}
                  />
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </nav>

      {/* Expand control lives at the bottom while collapsed: the brand row has
          no spare width for it there. */}
      {collapsed ? (
        <div className="px-2 pb-1">
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label="Expand sidebar"
            title="Expand sidebar"
            className="hidden w-full justify-center rounded-lg p-2 text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus lg:flex"
          >
            <ChevronsRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      {/* Account. Profile sits with it rather than in the nav list above: it is
          about the person signed in, which is what this whole block is. */}
      <div className={cn('shrink-0 border-t border-line py-3', collapsed ? 'px-2' : 'px-3')}>
        <ul className="mb-3 space-y-1">
          {FOOTER_NAV.map((item) => (
            <li key={item.key}>
              <NavItem
                item={item}
                active={section === item.key}
                collapsed={collapsed}
                onNavigate={onNavigate}
              />
            </li>
          ))}
        </ul>

        <div className={cn('flex items-center', collapsed ? 'justify-center' : 'gap-2.5')}>
          <span
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-line-strong bg-surface-2 text-sm font-bold text-brand-fg"
            title={collapsed ? student?.full_name || 'Student' : undefined}
          >
            {initial || <User className="h-4 w-4" aria-hidden="true" />}
          </span>
          {collapsed ? null : (
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold leading-tight text-fg">
                {student?.full_name || 'Student'}
              </div>
              <div className="truncate text-xs text-fg-muted">{student?.email}</div>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={handleLogout}
          title={collapsed ? 'Sign out' : undefined}
          className={cn(
            'mt-2 flex w-full items-center rounded-lg py-2 text-sm font-semibold text-fg-muted transition-colors',
            'hover:bg-danger-subtle hover:text-danger-fg',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
            collapsed ? 'justify-center px-0' : 'gap-3 px-3'
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
          {collapsed ? <span className="sr-only">Sign out</span> : <span>Sign out</span>}
        </button>
      </div>
    </div>
  );
};

export default AppSidebar;
