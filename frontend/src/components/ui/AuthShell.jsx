import React from 'react';
import { Compass } from 'lucide-react';
import Card from './Card';
import { cn } from '../../lib/cn';

const WIDTHS = { md: 'max-w-md', xl: 'max-w-xl' };

/**
 * Shared frame for the login and register pages, which previously duplicated
 * this wrapper, glow, brand mark, heading and card verbatim.
 */
export const AuthShell = ({ title, description, width = 'md', footer, children }) => (
  <div className="min-h-screen flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
    <div
      className="absolute top-1/4 left-1/4 w-80 h-80 max-w-full bg-brand-solid/10 rounded-full blur-3xl pointer-events-none"
      aria-hidden="true"
    />
    <div
      className="absolute bottom-1/4 right-1/4 w-80 h-80 max-w-full bg-accent-solid/10 rounded-full blur-3xl pointer-events-none"
      aria-hidden="true"
    />

    <div className={cn('w-full relative z-10', WIDTHS[width] || WIDTHS.md)}>
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-2xl btn-brand inline-flex items-center justify-center mb-4 shadow-e2">
          <Compass className="w-9 h-9 text-fg-on-solid" aria-hidden="true" />
        </div>
        <h1 className="text-3xl font-extrabold text-fg tracking-tight">{title}</h1>
        {description ? <p className="text-base text-fg-muted mt-2">{description}</p> : null}
      </div>

      <Card radius="2xl" padding="lg" className="shadow-e3">
        {children}
      </Card>

      {footer ? <div className="mt-6 text-center">{footer}</div> : null}
    </div>
  </div>
);

export default AuthShell;
