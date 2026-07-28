import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/cn';

const SIZES = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
};

/**
 * Decorative spinner only — it is aria-hidden and announces nothing. Wrap it in
 * PageSpinner/PaneSpinner (or a button with its own accessible label) so the
 * loading state is announced exactly once rather than twice.
 */
export const Spinner = ({ size = 'md', className }) => (
  <Loader2
    className={cn('animate-spin text-brand-fg', SIZES[size] || SIZES.md, className)}
    aria-hidden="true"
  />
);

export default Spinner;
