import React from 'react';
import { cn } from '../../lib/cn';

const TONES = {
  brand: 'bg-brand-subtle text-brand-subtle-fg',
  success: 'bg-success-subtle text-success-fg',
  accent: 'bg-accent-subtle text-accent-fg',
};

/** Dashboard statistic: a large value or icon, a label, and a sublabel. */
export const StatTile = ({ value, tone = 'brand', label, sublabel, className }) => (
  <div
    className={cn(
      'p-4 rounded-2xl bg-surface-3 border border-line flex items-center gap-4 min-w-0',
      className
    )}
  >
    <div
      className={cn(
        'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-xl shrink-0',
        TONES[tone] || TONES.brand
      )}
    >
      {value}
    </div>
    <div className="min-w-0">
      <div className="text-2xs font-semibold text-fg-muted uppercase">{label}</div>
      <div className="text-base font-bold text-fg truncate">{sublabel}</div>
    </div>
  </div>
);

export default StatTile;
