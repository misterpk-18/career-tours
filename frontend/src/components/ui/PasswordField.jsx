import React, { useId, useState } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';
import { cn } from '../../lib/cn';

/**
 * Password input owning its own visibility toggle. Replaces two copies of the
 * toggle logic, and the toggle now has an accessible name plus aria-pressed —
 * previously it announced only "button".
 *
 * The toggle is 40x40 so it clears the minimum touch-target size; the earlier
 * inline versions were roughly 24px.
 */
export const PasswordField = React.forwardRef(
  ({ id, label = 'Password', error, hint, required = false, className, ...rest }, ref) => {
    const [visible, setVisible] = useState(false);
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const hintId = `${inputId}-hint`;

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
          <div className="absolute top-0 left-0 h-[38px] flex items-center pl-3 text-fg-muted pointer-events-none">
            <Lock className="w-4 h-4" aria-hidden="true" />
          </div>
          <input
            ref={ref}
            id={inputId}
            type={visible ? 'text' : 'password'}
            required={required}
            aria-required={required || undefined}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className={cn(
              'field w-full rounded-xl text-sm pl-9 pr-11 py-2.5',
              error && 'border-danger-fg'
            )}
            {...rest}
          />
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? 'Hide password' : 'Show password'}
            aria-pressed={visible}
            className="absolute top-0 right-0 h-[38px] w-10 grid place-items-center text-fg-muted hover:text-fg rounded-r-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            {visible ? (
              <EyeOff className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Eye className="w-4 h-4" aria-hidden="true" />
            )}
          </button>
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

PasswordField.displayName = 'PasswordField';

export default PasswordField;
