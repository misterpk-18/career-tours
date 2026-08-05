import React from 'react';
import { cn } from '../../lib/cn';

/**
 * Dashboard statistic: a value, a label and a sublabel.
 *
 * No `tone`: the dashboard used brand/success/accent for three counts with no
 * categorical relationship, so the colour carried no information.
 */
export const StatTile = ({ value, label, sublabel, className }) => (
  <div
    className={cn(
      'p-4 rounded-xl bg-surface-3 border border-line flex items-center gap-4 min-w-0',
      className
    )}
  >
    <div
      className={cn(
        'w-12 h-12 rounded-lg flex items-center justify-center font-bold text-xl shrink-0',
        'bg-brand-subtle text-brand-subtle-fg'
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
