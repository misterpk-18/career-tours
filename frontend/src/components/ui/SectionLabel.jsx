import React from 'react';
import { cn } from '../../lib/cn';

/**
 * The small uppercase label above a block of content. `as` defaults to h4 but
 * should be set explicitly wherever the surrounding heading level differs.
 */
export const SectionLabel = ({ as: Tag = 'h4', icon: Icon, iconClassName, className, children, ...rest }) => (
  <Tag
    className={cn(
      'text-xs font-semibold text-fg-secondary uppercase tracking-wide mb-2 flex items-center gap-1.5',
      className
    )}
    {...rest}
  >
    {Icon ? <Icon className={cn('w-3.5 h-3.5', iconClassName)} aria-hidden="true" /> : null}
    {children}
  </Tag>
);

export default SectionLabel;
