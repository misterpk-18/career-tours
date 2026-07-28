import React from 'react';
import { Spinner } from './Spinner';
import { cn } from '../../lib/cn';

/** Full-section loading state, announced politely to assistive tech. */
export const PageSpinner = ({ message = 'Loading…', className }) => (
  <div
    role="status"
    aria-live="polite"
    className={cn('py-24 flex flex-col items-center justify-center text-fg-muted', className)}
  >
    <Spinner size="lg" className="mb-4" />
    <p className="text-sm font-medium">{message}</p>
  </div>
);

export default PageSpinner;
