import React from 'react';
import { Spinner } from './Spinner';

/**
 * Whole-viewport loading state used while the auth session rehydrates.
 * Replaces two divergent text-only copies in App.jsx (which said "Loading
 * CareerTours..." and "Loading..." respectively, and had no spinner).
 */
export const FullPageLoader = ({ message = 'Loading Career Tours…' }) => (
  <div
    role="status"
    aria-live="polite"
    className="min-h-screen bg-canvas flex flex-col items-center justify-center gap-3 text-fg-muted"
  >
    <Spinner size="lg" />
    <p className="text-sm font-medium">{message}</p>
  </div>
);

export default FullPageLoader;
