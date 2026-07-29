import React from 'react';
import Card from './Card';
import { cn } from '../../lib/cn';

/**
 * Page hero: eyebrow label, title, description and an optional actions slot.
 *
 * The `orbTone` prop and its blurred 320px orb are gone, along with
 * `eyebrowTone`: an eyebrow names a location ("Project"), which is not a state,
 * so it has no business being green. Colour here was decoration standing in for
 * hierarchy that size and weight already provide.
 */
export const HeroBanner = ({
  eyebrow,
  eyebrowIcon: EyebrowIcon,
  title,
  titleAs: Title = 'h1',
  description,
  actions,
  children,
  className,
}) => (
  <Card padding="lg" className={className}>
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
      <div className="space-y-2 min-w-0">
        {eyebrow ? (
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-line bg-surface-2 text-xs font-semibold text-fg-secondary">
            {EyebrowIcon ? <EyebrowIcon className="w-3.5 h-3.5" aria-hidden="true" /> : null}
            {eyebrow}
          </div>
        ) : null}

        <Title className="text-3xl lg:text-4xl font-bold text-fg tracking-tight">{title}</Title>

        {description ? (
          <p className="text-base text-fg-secondary max-w-3xl leading-relaxed">{description}</p>
        ) : null}
      </div>

      {actions ? <div className="flex flex-wrap items-center gap-3 shrink-0">{actions}</div> : null}
    </div>

    {children}
  </Card>
);

export default HeroBanner;
