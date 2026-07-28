import React from 'react';
import { cn } from '../../lib/cn';

/** Standard content width and rhythm for a full page. */
export const PageShell = ({ className, children }) => (
  <div className={cn('max-w-7xl mx-auto px-4 lg:px-8 py-8 space-y-8', className)}>{children}</div>
);

/** Narrower shell for single-message states (errors, empty pages). */
export const NarrowShell = ({ className, children }) => (
  <div className={cn('max-w-4xl mx-auto px-4 py-12', className)}>{children}</div>
);

export default PageShell;
