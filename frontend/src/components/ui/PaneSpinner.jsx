import React from 'react';
import { Spinner } from './Spinner';
import { cn } from '../../lib/cn';

/**
 * Loading state for one pane of a master/detail layout. Always bordered — the
 * careers page previously omitted the border its sibling states had, so the
 * panel edge flickered as the pane changed state.
 */
export const PaneSpinner = ({ message = 'Loading…', className }) => (
  <div
    role="status"
    aria-live="polite"
    className={cn(
      'surface-panel rounded-xl p-16 text-center text-fg-muted border border-line',
      className
    )}
  >
    <Spinner className="mx-auto mb-3" />
    <p className="text-sm">{message}</p>
  </div>
);

export default PaneSpinner;
