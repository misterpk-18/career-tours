import React from 'react';
import { cn } from '../../lib/cn';

const TONES = {
  brand: 'bg-brand-subtle border-brand-solid/40 text-brand-subtle-fg',
  success: 'bg-success-subtle border-success-fg/40 text-success-fg',
  warning: 'bg-warning-subtle border-warning-fg/40 text-warning-fg',
  danger: 'bg-danger-subtle border-danger-fg/40 text-danger-fg',
  accent: 'bg-accent-subtle border-accent-fg/40 text-accent-fg',
  neutral: 'bg-surface-3 border-line-strong text-fg-secondary',
};

/**
 * Larger than Badge — used for skill gaps, course levels and durations.
 * `dot` renders the small pulsing marker the skill-gap chips use.
 * Pass `tone={null}` with a className to supply a computed tone (see levelTone).
 */
export const Chip = ({ tone = 'neutral', icon: Icon, dot = false, className, children }) => (
  <span
    className={cn(
      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium',
      tone ? TONES[tone] || TONES.neutral : null,
      className
    )}
  >
    {dot ? (
      <span
        className="w-2 h-2 rounded-full bg-current opacity-80 animate-pulse-slow shrink-0"
        aria-hidden="true"
      />
    ) : null}
    {Icon ? <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> : null}
    {children}
  </span>
);

export default Chip;
