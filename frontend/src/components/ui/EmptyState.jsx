import React from 'react';
import Card from './Card';
import { cn } from '../../lib/cn';

const ICON_TONES = {
  brand: 'text-brand-fg',
  success: 'text-success-fg',
  warning: 'text-warning-fg',
  danger: 'text-danger-fg',
  neutral: 'text-fg-muted',
};

const SIZES = {
  sm: { padding: 'md', icon: 'w-10 h-10', title: 'text-base' },
  md: { padding: 'lg', icon: 'w-12 h-12', title: 'text-xl' },
};

/**
 * Consolidates eight inline empty states that had drifted across three variants
 * (differing radii, paddings and title sizes).
 *
 * `titleAs` is required so the heading level is chosen per page rather than
 * defaulting to something that breaks the outline.
 */
export const EmptyState = ({
  icon: Icon,
  iconTone = 'brand',
  title,
  titleAs: Title,
  description,
  action,
  size = 'md',
  className,
}) => {
  if (!Title) {
    throw new Error('EmptyState requires an explicit `titleAs` prop (h1-h4).');
  }

  const s = SIZES[size] || SIZES.md;

  return (
    <Card radius="3xl" padding={s.padding} className={cn('text-center', className)}>
      {Icon ? (
        <Icon className={cn(s.icon, 'mx-auto mb-3', ICON_TONES[iconTone] || ICON_TONES.brand)} aria-hidden="true" />
      ) : null}
      <Title className={cn('font-bold text-fg', s.title)}>{title}</Title>
      {description ? (
        <p className="text-sm text-fg-muted mt-2 mb-6 max-w-prose mx-auto">{description}</p>
      ) : null}
      {action ? <div className="flex flex-wrap items-center justify-center gap-3">{action}</div> : null}
    </Card>
  );
};

export default EmptyState;
