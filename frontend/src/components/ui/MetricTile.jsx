import React from 'react';
import { cn } from '../../lib/cn';

const ICON_WELLS = {
  brand: 'bg-brand-subtle text-brand-subtle-fg',
  success: 'bg-success-subtle text-success-fg',
  warning: 'bg-warning-subtle text-warning-fg',
  accent: 'bg-accent-subtle text-accent-fg',
  neutral: 'bg-surface-3 text-fg-muted',
};

/**
 * Label/value tile. Two documented layouts, replacing three variants that had
 * drifted apart (differing paddings and label sizes):
 *
 *   row    icon well beside the text (metrics with an icon)
 *   stack  compact centred pair (counts in a header strip)
 */
export const MetricTile = ({
  icon: Icon,
  iconTone = 'brand',
  label,
  value,
  valueTone = 'text-fg',
  layout = 'row',
  className,
}) => {
  if (layout === 'stack') {
    return (
      <div
        className={cn(
          'px-4 py-2 rounded-2xl bg-surface-3 border border-line text-center min-w-0',
          className
        )}
      >
        <div className="text-2xs font-semibold text-fg-muted uppercase">{label}</div>
        <div className={cn('text-base font-bold', valueTone)}>{value}</div>
      </div>
    );
  }

  return (
    <div
      className={cn('p-4 rounded-2xl bg-surface-3 border border-line flex items-center gap-3', className)}
    >
      {Icon ? (
        <div
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
            ICON_WELLS[iconTone] || ICON_WELLS.brand
          )}
        >
          <Icon className="w-5 h-5" aria-hidden="true" />
        </div>
      ) : null}
      <div className="min-w-0">
        <div className="text-2xs font-semibold text-fg-muted uppercase">{label}</div>
        <div className={cn('text-base font-bold truncate', valueTone)}>{value}</div>
      </div>
    </div>
  );
};

export default MetricTile;
