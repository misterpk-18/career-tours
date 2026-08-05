import React from 'react';
import { cn } from '../../lib/cn';

// No `accent` (purple is gone) and no `success`: the only success caller was the
// "Strengths" list, and a strength is a category, not a state. `warning` survives
// for skill gaps, which genuinely are "needs attention".
const TONES = {
  neutral: 'bg-surface-3 border-line-strong text-fg-secondary',
  brand: 'bg-brand-subtle border-brand-solid/40 text-brand-subtle-fg',
  warning: 'bg-warning-subtle border-warning-fg/40 text-warning-fg',
  danger: 'bg-danger-subtle border-danger-fg/40 text-danger-fg',
};

/**
 * Larger than Badge — used for skills, course levels and durations.
 *
 * The `dot` prop and its `animate-pulse-slow` marker are gone: every skill-gap
 * chip pulsed in unison, which reads as urgency the data does not carry. The
 * `tone={null}` escape hatch is gone too — it existed so a caller could inject an
 * arbitrary colour through className, which is how course difficulty acquired a
 * purple/amber/green traffic light.
 */
export const Chip = ({ tone = 'neutral', icon: Icon, className, children }) => {
  if (!TONES[tone]) {
    throw new Error(
      `Chip: unknown tone "${tone}". Tones encode state: neutral | brand | warning | danger.`
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium',
        TONES[tone],
        className
      )}
    >
      {Icon ? <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" /> : null}
      {children}
    </span>
  );
};

export default Chip;
