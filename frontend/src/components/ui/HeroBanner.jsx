import React from 'react';
import Card from './Card';
import { cn } from '../../lib/cn';

const ORB_TONES = {
  brand: 'bg-brand-solid/10',
  success: 'bg-success-solid/10',
  accent: 'bg-accent-solid/10',
};

const EYEBROW_TONES = {
  brand: 'bg-brand-subtle border-brand-solid/30 text-brand-subtle-fg',
  success: 'bg-success-subtle border-success-fg/30 text-success-fg',
  accent: 'bg-accent-subtle border-accent-fg/30 text-accent-fg',
};

/**
 * Page hero: eyebrow chip, title, description and an optional actions slot.
 * Consolidates three near-identical inline banners that differed only in the
 * decorative orb tint and the eyebrow icon.
 */
export const HeroBanner = ({
  eyebrow,
  eyebrowIcon: EyebrowIcon,
  eyebrowTone = 'brand',
  title,
  titleAs: Title = 'h1',
  description,
  orbTone = 'brand',
  actions,
  children,
  className,
}) => (
  <Card radius="3xl" padding="lg" className={cn('relative overflow-hidden', className)}>
    {orbTone ? (
      <div
        className={cn(
          'absolute top-0 right-0 w-80 h-80 max-w-full rounded-full blur-3xl pointer-events-none',
          ORB_TONES[orbTone] || ORB_TONES.brand
        )}
        aria-hidden="true"
      />
    ) : null}

    <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
      <div className="space-y-2 min-w-0">
        {eyebrow ? (
          <div
            className={cn(
              'inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold',
              EYEBROW_TONES[eyebrowTone] || EYEBROW_TONES.brand
            )}
          >
            {EyebrowIcon ? <EyebrowIcon className="w-3.5 h-3.5" aria-hidden="true" /> : null}
            {eyebrow}
          </div>
        ) : null}

        <Title className="text-3xl lg:text-4xl font-extrabold text-fg tracking-tight">{title}</Title>

        {description ? (
          <p className="text-base text-fg-secondary max-w-3xl leading-relaxed">{description}</p>
        ) : null}
      </div>

      {actions ? <div className="flex flex-wrap items-center gap-3 shrink-0">{actions}</div> : null}
    </div>

    {children ? <div className="relative z-10">{children}</div> : null}
  </Card>
);

export default HeroBanner;
