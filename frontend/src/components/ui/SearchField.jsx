import React from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '../../lib/cn';

/**
 * Filter-as-you-type input for a list already held in memory.
 *
 * Deliberately not debounced and not tied to a request: the catalogue arrives
 * in one response, so filtering is a synchronous array pass and any delay would
 * be latency invented for its own sake.
 *
 * `count` and `total` render the result of the filter next to the control that
 * caused it — without it, a query that matches nothing looks the same as a list
 * that failed to load.
 */
export const SearchField = ({
  value,
  onChange,
  placeholder = 'Search…',
  label,
  count,
  total,
  className,
}) => (
  <div className={cn('space-y-2', className)}>
    <div className="relative">
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-muted"
        aria-hidden="true"
      />

      <input
        type="search"
        value={value}
        aria-label={label || placeholder}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        // type="search" gives Escape-to-clear and the native clear affordance in
        // some browsers; the button below guarantees one everywhere.
        className="field w-full rounded-lg py-2.5 pl-9 pr-10 text-sm"
      />

      {value ? (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      ) : null}
    </div>

    {total != null ? (
      // aria-live so the count is announced as it changes: a sighted user sees
      // the list shrink, and this is the equivalent signal.
      <p className="text-xs text-fg-muted" aria-live="polite">
        {value ? `${count} of ${total} match “${value}”` : `${total} in total`}
      </p>
    ) : null}
  </div>
);

export default SearchField;
