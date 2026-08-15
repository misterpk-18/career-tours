import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Compass, FolderKanban, GraduationCap, LayoutDashboard, Loader2, Search } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { projectsAPI } from '../services/api';
import { projectNav, resolveRoute } from '../lib/nav';
import { cn } from '../lib/cn';

const MAX_RESULTS = 8;

const ICONS = {
  dashboard: LayoutDashboard,
  project: FolderKanban,
  careers: Compass,
  courses: GraduationCap,
};

/**
 * What a query is matched against.
 *
 * Every field is a string the user could plausibly type. `keywords` exists so a
 * destination is reachable by the word for the thing it shows ("jobs", "gap")
 * and not only by its own label.
 */
const matches = (entry, query) =>
  query
    .split(/\s+/)
    .filter(Boolean)
    .every((term) => entry.haystack.includes(term));

export const GlobalSearch = ({ className }) => {
  const { student } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const listId = useId();

  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [projects, setProjects] = useState(null);
  const [loading, setLoading] = useState(false);

  const inputRef = useRef(null);
  const containerRef = useRef(null);

  /**
   * Fetched on focus, not on mount.
   *
   * The shell wraps every page and stays mounted across navigations, so
   * fetching on mount would both add a request to the first paint and then go
   * stale the moment a project is created. Re-reading on focus keeps it current
   * for the cost of one GET at the moment the user actually asks. The previous
   * list stays on screen while it reloads, so there is no flash of empty.
   *
   * Held in component state only — the project list is server-owned, so it must
   * not be cached in localStorage (see lib/storage.js).
   */
  const loadProjects = useCallback(async () => {
    if (loading || !student?.student_id) return;

    setLoading(true);
    try {
      setProjects(await projectsAPI.getByStudentId(student.student_id));
    } catch (err) {
      console.error('Global search could not load projects:', err);
      // Whatever was already listed stays listed. Replacing it with [] would
      // turn a transient network failure into "you have no projects".
      setProjects((current) => current || []);
    } finally {
      setLoading(false);
    }
  }, [loading, student?.student_id]);

  const route = resolveRoute(pathname);

  const entries = useMemo(() => {
    const items = [
      {
        id: 'nav-dashboard',
        kind: 'dashboard',
        label: 'Dashboard',
        detail: 'All of your projects',
        to: '/',
        keywords: 'home projects overview',
      },
      // The project pages are route-scoped, so they are only offered while a
      // project is open. Offering them otherwise would mean guessing an id.
      ...projectNav(route.projectId).map((item) => ({
        id: `nav-${item.key}`,
        kind: item.key,
        label: item.label,
        detail: 'Current project',
        to: item.to,
        keywords:
          item.key === 'careers'
            ? 'career matches jobs occupations gaps skills'
            : item.key === 'courses'
              ? 'courses learning path syllabus training'
              : 'project workspace resume skills',
      })),
      ...(projects || []).map((project) => ({
        id: `project-${project.project_id}`,
        kind: 'project',
        label: project.project_name,
        detail: project.description || 'Project',
        to: `/projects/${project.project_id}`,
        keywords: project.project_id,
      })),
    ];

    return items.map((item) => ({
      ...item,
      haystack: `${item.label} ${item.detail} ${item.keywords}`.toLowerCase(),
    }));
  }, [projects, route.projectId]);

  const results = useMemo(() => {
    const trimmed = query.trim().toLowerCase();

    if (!trimmed) return entries.slice(0, MAX_RESULTS);

    return entries.filter((entry) => matches(entry, trimmed)).slice(0, MAX_RESULTS);
  }, [entries, query]);

  // Clamped rather than reset to 0: the list re-filters on every keystroke, and
  // an index left pointing past the end would send Enter nowhere.
  useEffect(() => {
    setActiveIndex((current) => (current < results.length ? current : 0));
  }, [results.length]);

  // Close on an outside click. Pointerdown rather than click so selecting a
  // result by mouse isn't cancelled by the close that a click would fire first.
  useEffect(() => {
    if (!open) return undefined;

    const onPointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };

    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  // Cmd/Ctrl+K from anywhere. Deliberately not bare "/" — that would swallow the
  // key while someone is typing a project description in a modal.
  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const go = (entry) => {
    if (!entry) return;
    setOpen(false);
    setQuery('');
    inputRef.current?.blur();
    navigate(entry.to);
  };

  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      if (!results.length) return;

      const step = event.key === 'ArrowDown' ? 1 : -1;
      setActiveIndex((current) => (current + step + results.length) % results.length);
      return;
    }

    if (event.key === 'Enter' && open) {
      event.preventDefault();
      go(results[activeIndex]);
    }
  };

  const activeId = open && results[activeIndex] ? `${listId}-${results[activeIndex].id}` : undefined;

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-muted"
        aria-hidden="true"
      />

      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeId}
        aria-autocomplete="list"
        aria-label="Search projects and pages"
        placeholder="Search projects and pages…"
        value={query}
        onFocus={() => {
          setOpen(true);
          loadProjects();
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        className="field w-full rounded-lg py-2 pl-9 pr-14 text-sm"
      />

      <kbd
        aria-hidden="true"
        className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line bg-surface-2 px-1.5 py-0.5 font-sans text-2xs font-semibold text-fg-muted sm:block"
      >
        ⌘K
      </kbd>

      {open ? (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-line bg-surface shadow-e3 animate-fade-in">
          {loading && !results.length ? (
            <p className="flex items-center gap-2 px-3 py-3 text-sm text-fg-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading your projects…
            </p>
          ) : results.length === 0 ? (
            <p className="px-3 py-3 text-sm text-fg-muted">
              Nothing matches “{query.trim()}”.
            </p>
          ) : (
            <ul id={listId} role="listbox" aria-label="Search results" className="max-h-80 overflow-y-auto p-1.5">
              {results.map((entry, index) => {
                const Icon = ICONS[entry.kind] || FolderKanban;
                const active = index === activeIndex;

                return (
                  <li key={entry.id}>
                    <button
                      type="button"
                      id={`${listId}-${entry.id}`}
                      role="option"
                      aria-selected={active}
                      // Mouse hover moves the selection so the keyboard and the
                      // pointer never highlight two different rows at once.
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => go(entry)}
                      className={cn(
                        'flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors',
                        active ? 'bg-brand-subtle text-brand-subtle-fg' : 'text-fg-secondary'
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-fg">{entry.label}</span>
                        <span className="block truncate text-xs text-fg-muted">{entry.detail}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default GlobalSearch;
