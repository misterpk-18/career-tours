import React from 'react';
import { cn } from '../../lib/cn';

/**
 * Staggered entrance for a list.
 *
 * The stagger is an inline animation-delay rather than a per-item class, because
 * the delay is a function of the index and Tailwind cannot generate an arbitrary
 * one. The animation itself is a class, so the reduced-motion block in index.css
 * still flattens it — a delay on a 0.01ms animation is imperceptible either way.
 *
 * Capped at ten steps: past about 400ms of cumulative delay a list stops feeling
 * orchestrated and starts feeling slow, and a 40-item list would otherwise make
 * the last item wait two seconds.
 */
const MAX_STEPS = 10;

export const Reveal = ({ index = 0, step = 40, className, as: Tag = 'div', children, ...rest }) => (
  <Tag
    className={cn('animate-rise-in', className)}
    style={{ animationDelay: `${Math.min(index, MAX_STEPS) * step}ms` }}
    {...rest}
  >
    {children}
  </Tag>
);

export default Reveal;
