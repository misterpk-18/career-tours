import React, { useId } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/cn';

/**
 * Labelled `<select>`, matching TextField's label wiring and `.field` styling.
 *
 * Separate from TextField rather than `as="select"`: TextField spreads props
 * onto its tag but never renders children, so a select built that way would
 * silently have no options.
 *
 * `options` is `[{ value, label }]`. A `placeholder` becomes an empty-valued
 * first option, which is how "not answered yet" stays distinguishable from a
 * real choice — an optional profile field must be able to hold no answer.
 */
export const SelectField = ({
  id,
  label,
  options = [],
  placeholder,
  hint,
  error,
  className,
  ...rest
}) => {
  const generatedId = useId();
  const selectId = id || generatedId;
  const errorId = `${selectId}-error`;
  const hintId = `${selectId}-hint`;

  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;

  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={selectId} className="block text-sm font-medium text-fg-secondary">
        {label}
      </label>

      <div className="relative">
        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'field w-full appearance-none rounded-xl px-3.5 py-2.5 pr-10 text-sm',
            error && 'border-danger-fg'
          )}
          {...rest}
        >
          {placeholder ? <option value="">{placeholder}</option> : null}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-muted"
          aria-hidden="true"
        />
      </div>

      {hint ? (
        <p id={hintId} className="text-xs text-fg-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs font-medium text-danger-fg">
          {error}
        </p>
      ) : null}
    </div>
  );
};

export default SelectField;
