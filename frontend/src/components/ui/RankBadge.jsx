import React from 'react';
import { cn } from '../../lib/cn';

const SIZES = {
  sm: 'w-7 h-7 text-xs',
  md: 'w-8 h-8 text-sm',
};

/**
 * The "#1"-style rank marker. Always `shrink-0` — one of the three inline copies
 * omitted it, so a long neighbouring title could squash the badge.
 */
export const RankBadge = ({ rank, size = 'md', className }) => (
  <div
    className={cn(
      'rounded-xl bg-brand-subtle text-brand-subtle-fg font-extrabold flex items-center justify-center border border-brand-solid/30 shrink-0',
      SIZES[size] || SIZES.md,
      className
    )}
  >
    #{rank}
  </div>
);

export default RankBadge;
