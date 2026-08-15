import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import AppSidebar from './AppSidebar';
import AppTopBar from './AppTopBar';
import useBodyScrollLock from '../hooks/useBodyScrollLock';
import { getSidebarCollapsed, setSidebarCollapsed } from '../lib/storage';
import { cn } from '../lib/cn';

/**
 * The application shell: a fixed nav rail, a sticky top bar, and the page.
 *
 * Replaces the full-width Navbar. The rail is `fixed` rather than a flex column
 * so the page scrolls under a nav that stays put — with a flex row the whole
 * shell scrolls together and the nav leaves the screen on any long page.
 *
 * Below `lg` the rail becomes an overlay drawer. The same AppSidebar renders in
 * both, so the two layouts cannot drift apart.
 */
export const AppLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(getSidebarCollapsed);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { pathname } = useLocation();

  useBodyScrollLock(drawerOpen);

  // Any navigation closes the drawer — it covers the page it just navigated to.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!drawerOpen) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') setDrawerOpen(false);
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen]);

  const toggleCollapse = () => {
    setCollapsed((current) => {
      const next = !current;
      setSidebarCollapsed(next);
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-canvas">
      {/* Rail — desktop */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 hidden transition-[width] duration-200 lg:block',
          collapsed ? 'w-[4.5rem]' : 'w-60'
        )}
      >
        <AppSidebar collapsed={collapsed} onToggleCollapse={toggleCollapse} />
      </aside>

      {/* Rail — mobile drawer. Kept out of the DOM while closed so its links are
          not in the tab order behind the scrim. */}
      {drawerOpen ? (
        <div className="lg:hidden">
          <div
            className="fixed inset-0 z-40 scrim animate-fade-in"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="fixed inset-y-0 left-0 z-50 w-60 animate-fade-in"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
          >
            <AppSidebar collapsed={false} onNavigate={() => setDrawerOpen(false)} />
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close navigation"
              className="absolute -right-11 top-3 rounded-lg bg-surface p-2 text-fg-secondary shadow-e2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </aside>
        </div>
      ) : null}

      {/* Page */}
      <div className={cn('transition-[padding] duration-200', collapsed ? 'lg:pl-[4.5rem]' : 'lg:pl-60')}>
        <AppTopBar onOpenSidebar={() => setDrawerOpen(true)} />
        <main>{children}</main>
      </div>
    </div>
  );
};

export default AppLayout;
