import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * Catches render-time exceptions. Without this a single throw in any page
 * unmounts the whole tree and leaves a blank screen with no recovery path.
 *
 * The only class component in the codebase — React has no hook equivalent for
 * componentDidCatch.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info?.componentStack);
  }

  render() {
    const { error } = this.state;
    const { children, fallback } = this.props;

    if (!error) return children;
    if (fallback) return fallback;

    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center px-4 py-12">
        <div className="surface-glass rounded-3xl border border-line p-8 text-center max-w-lg">
          <AlertTriangle className="w-12 h-12 text-danger-fg mx-auto mb-3" aria-hidden="true" />
          <h1 className="text-xl font-bold text-fg">Something went wrong</h1>
          <p className="text-sm text-fg-muted mt-2 mb-6">
            The page hit an unexpected error and stopped rendering. Reloading usually clears it.
          </p>
          {/* A full reload rather than a state reset: the component tree that
              threw may hold inconsistent state, so remounting it can re-throw. */}
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="btn-brand px-6 py-3 rounded-xl text-sm font-semibold inline-flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            Reload the page
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
