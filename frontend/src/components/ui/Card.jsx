import React from 'react';
import { cn } from '../../lib/cn';

const RADII = { xl: 'rounded-xl', '2xl': 'rounded-2xl', '3xl': 'rounded-3xl' };
const PADDING = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };

/**
 * Surface container.
 *
 * `variant` is a prop rather than something passed through className because the
 * three surface classes are hand-written CSS, not Tailwind utilities —
 * tailwind-merge cannot resolve a conflict between two of them, so a caller
 * passing both would produce an unpredictable cascade.
 *
 *   panel       static glass (page heroes, detail panels)
 *   interactive glass with a hover lift (clickable cards)
 *   solid       opaque; use INSIDE glass, since glass over glass on a light
 *               background is indistinguishable from opaque anyway
 */
const VARIANTS = {
  panel: 'surface-glass',
  interactive: 'surface-glass-interactive',
  solid: 'bg-surface shadow-e1',
};

export const Card = ({
  as: Tag = 'div',
  variant = 'panel',
  radius = '2xl',
  padding = 'md',
  bordered = true,
  className,
  children,
  ...rest
}) => (
  <Tag
    className={cn(
      VARIANTS[variant] || VARIANTS.panel,
      RADII[radius] || RADII['2xl'],
      PADDING[padding] ?? PADDING.md,
      bordered && 'border border-line',
      className
    )}
    {...rest}
  >
    {children}
  </Tag>
);

export default Card;
