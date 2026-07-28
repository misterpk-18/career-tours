import React, { useId } from 'react';
import { cn } from '../../lib/cn';

/**
 * Labelled text input.
 *
 * The id is generated when not supplied and wired to <label htmlFor>, so an
 * input without an accessible name cannot be constructed through this component
 * — all 11 inputs in the app previously had unassociated labels.
 */
export const TextField = React.forwardRef(
  (
    {
      id,
      label,
      icon: Icon,
      error,
      hint,
      required = false,
      className,
      inputClassName,
      as = 'input',
      rows,
      ...rest
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const hintId = `${inputId}-hint`;
    const Tag = as;

    const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;

    return (
      <div className={cn('space-y-1.5', className)}>
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold text-fg-secondary uppercase tracking-wider"
        >
          {label}
          {required ? (
            <span className="text-danger-fg ml-0.5" aria-hidden="true">
              *
            </span>
          ) : null}
        </label>

        <div className="relative">
          {Icon ? (
            <div className="absolute top-0 left-0 h-[38px] flex items-center pl-3 text-fg-muted pointer-events-none">
              <Icon className="w-4 h-4" aria-hidden="true" />
            </div>
          ) : null}
          <Tag
            ref={ref}
            id={inputId}
            rows={rows}
            required={required}
            aria-required={required || undefined}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className={cn(
              'field w-full rounded-xl text-sm px-3.5 py-2.5',
              Icon && 'pl-9',
              error && 'border-danger-fg',
              inputClassName
            )}
            {...rest}
          />
        </div>

        {hint ? (
          <p id={hintId} className="text-xs text-fg-muted">
            {hint}
          </p>
        ) : null}
        {error ? (
          <p id={errorId} className="text-xs text-danger-fg font-medium">
            {error}
          </p>
        ) : null}
      </div>
    );
  }
);

TextField.displayName = 'TextField';

export default TextField;
