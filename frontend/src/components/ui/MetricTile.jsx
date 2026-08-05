import React from 'react';
import { cn } from '../../lib/cn';

/**
 * Label/value tile. Two documented layouts, replacing three variants that had
 * drifted apart (differing paddings and label sizes):
 *
 *   row    icon well beside the text (metrics with an icon)
 *   stack  compact centred pair (counts in a header strip)
 */
export const MetricTile = ({
  icon: Icon,
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
          'px-4 py-2 rounded-xl bg-surface-3 border border-line text-center min-w-0',
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
      className={cn('p-4 rounded-xl bg-surface-3 border border-line flex items-center gap-3', className)}
    >
      {Icon ? (
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center shrink-0',
            'bg-surface-2 text-fg-muted'
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
