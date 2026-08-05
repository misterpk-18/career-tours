import React from 'react';
import { cn } from '../../lib/cn';

const PADDING = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };

/**
 * Surface container.
 *
 * `variant` is a prop rather than something passed through className because the
 * surface classes are hand-written CSS, not Tailwind utilities — tailwind-merge
 * cannot resolve a conflict between two of them, so a caller passing both would
 * produce an unpredictable cascade.
 *
 *   panel       static surface (page heroes, detail panels)
 *   interactive surface with a hover response (clickable cards)
 *   solid       flat; for a card nested directly inside another card
 *
 * There is no `radius` prop: every card is `rounded-xl`. A `radius` choice per
 * call site produced a course card nesting 3xl -> 2xl -> xl -> lg -> full.
 * There is no `bordered` prop either — the variant classes own the border, and
 * `bordered` was declaring a second, competing one.
 */
const VARIANTS = {
  panel: 'surface-panel',
  interactive: 'surface-panel-interactive',
  solid: 'bg-surface border border-line',
};

export const Card = ({
  as: Tag = 'div',
  variant = 'panel',
  padding = 'md',
  className,
  children,
  ...rest
}) => (
  <Tag
    className={cn(
      VARIANTS[variant] || VARIANTS.panel,
      'rounded-xl',
      PADDING[padding] ?? PADDING.md,
      className
    )}
    {...rest}
  >
    {children}
  </Tag>
);

export default Card;
