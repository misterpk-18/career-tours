import React from 'react';
import { cn } from '../../lib/cn';

const SIZES = {
  sm: 'text-base',
  md: 'text-xl',
  lg: 'text-2xl',
};

/**
 * Section heading with an optional right-hand slot.
 *
 * `as` has NO default on purpose: the heading level must be a decision at every
 * call site. Two pages previously inverted their outline (h1 -> h2 -> h3 -> h2),
 * which is invisible in the browser because Tailwind sets the size, not the tag.
 */
export const SectionHeading = ({ as: Tag, icon: Icon, iconClassName, right, size = 'md', className, children }) => {
  if (!Tag) {
    throw new Error('SectionHeading requires an explicit `as` prop (h1-h4) so the document outline stays correct.');
  }

  return (
    <div className={cn('flex items-center justify-between gap-4 flex-wrap', className)}>
      <Tag className={cn('font-bold text-fg flex items-center gap-2', SIZES[size] || SIZES.md)}>
        {Icon ? <Icon className={cn('w-5 h-5', iconClassName)} aria-hidden="true" /> : null}
        {children}
      </Tag>
      {right ? <div className="text-xs text-fg-muted font-normal">{right}</div> : null}
    </div>
  );
};

export default SectionHeading;
