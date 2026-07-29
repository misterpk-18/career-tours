import React from 'react';
import { cn } from '../../lib/cn';

const TONES = {
  brand: 'bg-brand-subtle text-brand-subtle-fg border-brand-solid/30',
  success: 'bg-success-subtle text-success-fg border-success-fg/40',
  warning: 'bg-warning-subtle text-warning-fg border-warning-fg/40',
  danger: 'bg-danger-subtle text-danger-fg border-danger-fg/40',
  neutral: 'bg-surface-3 text-fg-muted border-line',
};

/** Small status pill. `mono` is for identifiers such as truncated UUIDs. */
export const Badge = ({ tone = 'neutral', icon: Icon, mono = false, className, children }) => {
  if (!TONES[tone]) {
    throw new Error(
      `Badge: unknown tone "${tone}". Tones encode state: neutral | brand | success | warning | danger.`
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-2xs font-semibold whitespace-nowrap',
        mono && 'font-mono',
        TONES[tone],
        className
      )}
    >
      {Icon ? <Icon className="w-3 h-3 shrink-0" aria-hidden="true" /> : null}
      {children}
    </span>
  );
};

export default Badge;
