import React from 'react';
import { Compass } from 'lucide-react';
import Card from './Card';
import { cn } from '../../lib/cn';

const WIDTHS = { md: 'max-w-md', xl: 'max-w-xl' };

/**
 * Shared frame for the login and register pages, which previously duplicated
 * this wrapper, brand mark, heading and card verbatim.
 *
 * The two diagonally-opposed blurred orbs (one indigo, one purple) that used to
 * sit behind the card are gone: they were the only thing on these pages other
 * than the form itself.
 */
export const AuthShell = ({ title, description, width = 'md', footer, children }) => (
  <div className="min-h-screen flex flex-col justify-center items-center px-4 py-12">
    <div className={cn('w-full', WIDTHS[width] || WIDTHS.md)}>
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-xl btn-brand inline-flex items-center justify-center mb-4">
          <Compass className="w-9 h-9 text-fg-on-solid" aria-hidden="true" />
        </div>
        <h1 className="text-3xl font-bold text-fg tracking-tight">{title}</h1>
        {description ? <p className="text-base text-fg-muted mt-2">{description}</p> : null}
      </div>

      <Card padding="lg">{children}</Card>

      {footer ? <div className="mt-6 text-center">{footer}</div> : null}
    </div>
  </div>
);

export default AuthShell;
