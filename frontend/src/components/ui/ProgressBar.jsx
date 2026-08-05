import React from 'react';
import { toPct } from '../../lib/format';
import { cn } from '../../lib/cn';

/**
 * Percentage bar with an optional caption row.
 *
 * The value is clamped inside the component via toPct, so an out-of-range value
 * from the API can no longer overflow the track — the careers page previously
 * fed an unclamped Math.round straight into the inline width.
 */
export const ProgressBar = ({ value, label, valueLabel, valueTone = 'text-fg', className }) => {
  const pct = toPct(value);

  return (
    <div className={cn('space-y-1.5', className)}>
      {(label || valueLabel) && (
        <div className="flex items-center justify-between text-xs font-semibold">
          {label ? <span className="text-fg-muted">{label}</span> : <span />}
          {valueLabel ? <span className={cn('font-bold', valueTone)}>{valueLabel}</span> : null}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || 'Progress'}
        className="w-full bg-surface-3 h-2 rounded-full overflow-hidden border border-line"
      >
        <div
          className="bg-brand-solid h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
